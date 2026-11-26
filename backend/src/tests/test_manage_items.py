"""
Tests for managing label types after project creation and for deleting artifacts.
"""
from sqlalchemy import func, select

from src.conftest import RequestHandler
from src.models import db
from src.models.item_models import Artifact, Label, LabelType, Labelling, label_to_theme

# Test data (lama_test.sql):
# project 1: label types 1 'Technology' and 2 'Emotion'; user 2 is admin, user 6 is not
# project 5: a single label type 7 'Words'; user 1 is admin


def _count(app, stmt):
    with app.app_context():
        return db.session.scalar(stmt)


# --- Label types -------------------------------------------------------------------

def test_create_label_type(app, client):
    handler = RequestHandler(app, client, 2)
    response = handler.post('/labeltype/create', {'p_id': 1, 'name': 'Sentiment'}, True)
    assert response.status_code == 201
    assert response.json['name'] == 'Sentiment'
    assert _count(app, select(func.count()).select_from(LabelType).where(LabelType.p_id == 1)) == 3


def test_create_label_type_validation(app, client):
    handler = RequestHandler(app, client, 2)
    # Duplicate name
    assert handler.post('/labeltype/create', {'p_id': 1, 'name': 'Emotion'}, True).status_code == 400
    # Empty, whitespace and forbidden characters
    assert handler.post('/labeltype/create', {'p_id': 1, 'name': ''}, True).status_code == 400
    assert handler.post('/labeltype/create', {'p_id': 1, 'name': ' Emotion2'}, True).status_code == 400
    assert handler.post('/labeltype/create', {'p_id': 1, 'name': 'a;b'}, True).status_code == 511
    # Missing name
    assert handler.post('/labeltype/create', {'p_id': 1}, True).status_code == 400


def test_label_type_management_requires_admin(app, client):
    # User 6 is a member, but not an admin, of project 1
    handler = RequestHandler(app, client, 6)
    assert handler.post('/labeltype/create', {'p_id': 1, 'name': 'New'}, True).status_code == 401
    assert handler.patch('/labeltype/rename', {'p_id': 1, 'lt_id': 1, 'name': 'New'}, True).status_code == 401
    assert handler.post('/labeltype/delete', {'p_id': 1, 'lt_id': 1}, True).status_code == 401


def test_label_type_management_frozen_project(app, client):
    with app.app_context():
        from src.models.project_models import Project
        db.session.get(Project, 1).frozen = True
        db.session.commit()
    handler = RequestHandler(app, client, 2)
    assert handler.post('/labeltype/create', {'p_id': 1, 'name': 'New'}, True).status_code == 400


def test_rename_label_type(app, client):
    handler = RequestHandler(app, client, 2)
    response = handler.patch('/labeltype/rename', {'p_id': 1, 'lt_id': 1, 'name': 'Tech'}, True)
    assert response.status_code == 200
    with app.app_context():
        assert db.session.get(LabelType, 1).name == 'Tech'

    # Name already used by the other label type of the project
    assert handler.patch('/labeltype/rename', {'p_id': 1, 'lt_id': 1, 'name': 'Emotion'}, True).status_code == 400
    # Label type of another project
    assert handler.patch('/labeltype/rename', {'p_id': 1, 'lt_id': 3, 'name': 'X'}, True).status_code == 400


def test_delete_label_type(app, client):
    with app.app_context():
        label_ids = db.session.scalars(select(Label.id).where(Label.lt_id == 2)).all()
        n_other_labellings = db.session.scalar(
            select(func.count()).select_from(Labelling).where(Labelling.p_id == 1, Labelling.lt_id == 1))
    assert label_ids

    handler = RequestHandler(app, client, 2)
    response = handler.post('/labeltype/delete', {'p_id': 1, 'lt_id': 2}, True)
    assert response.status_code == 200

    with app.app_context():
        assert db.session.get(LabelType, 2) is None
        assert db.session.scalar(select(func.count()).select_from(Label).where(Label.lt_id == 2)) == 0
        assert db.session.scalar(select(func.count()).select_from(Labelling).where(Labelling.lt_id == 2)) == 0
        assert db.session.scalar(select(func.count()).select_from(label_to_theme)
                                 .where(label_to_theme.c.l_id.in_(label_ids))) == 0
        LabelChange = Label.__change__
        assert db.session.scalar(select(func.count()).select_from(LabelChange)
                                 .where(LabelChange.i_id.in_(label_ids))) == 0
        # The other label type is untouched
        assert db.session.scalar(
            select(func.count()).select_from(Labelling).where(Labelling.p_id == 1, Labelling.lt_id == 1)
        ) == n_other_labellings

    # The project pages still work
    assert handler.get('/labeltype/allWithLabels', {'p_id': 1}, True).status_code == 200
    assert handler.get('/project/settings', {'p_id': 1}, True).status_code == 200


def test_delete_last_label_type(app, client):
    handler = RequestHandler(app, client, 1)
    assert handler.post('/labeltype/delete', {'p_id': 5, 'lt_id': 7}, True).status_code == 400


def test_settings_contains_label_type_counts(app, client):
    response = RequestHandler(app, client, 2).get('/project/settings', {'p_id': 1}, True)
    assert response.status_code == 200
    for label_type in response.json['labelType']:
        lt_id = label_type['label_type_id']
        assert label_type['n_labellings'] == _count(
            app, select(func.count()).select_from(Labelling).where(Labelling.lt_id == lt_id))
        assert label_type['n_labels'] == _count(
            app, select(func.count()).select_from(Label).where(Label.lt_id == lt_id, Label.deleted == False))


# --- Artifacts -----------------------------------------------------------------------

def test_delete_artifact(app, client):
    assert _count(app, select(func.count()).select_from(Labelling).where(Labelling.a_id == 1)) > 0

    handler = RequestHandler(app, client, 2)
    response = handler.post('/artifact/delete', {'p_id': 1, 'a_ids': [1]}, True)
    assert response.status_code == 200
    assert response.json['deleted'] == [1]

    with app.app_context():
        assert db.session.get(Artifact, 1) is None
        assert db.session.scalar(select(func.count()).select_from(Labelling).where(Labelling.a_id == 1)) == 0
        ArtifactChange = Artifact.__change__
        assert db.session.scalar(select(func.count()).select_from(ArtifactChange)
                                 .where(ArtifactChange.i_id == 1)) == 0

    # The artifact management page still works
    response = handler.get('/artifact/artifactmanagement',
                           {'p_id': 1, 'page': 1, 'page_size': 5, 'seek_index': 0, 'seek_page': 0}, True)
    assert response.status_code == 200


def test_delete_artifact_deletes_split_children(app, client):
    handler = RequestHandler(app, client, 2)
    with app.app_context():
        parent = db.session.get(Artifact, 2)
        identifier, data = parent.identifier, parent.data
    # Split artifact 2, then split the child again
    child = handler.post('/artifact/split', {'p_id': 1, 'parent_id': 2, 'identifier': identifier,
                                             'start': 0, 'end': 20, 'data': data[0:20]}, True)
    assert child.status_code == 200
    child_id = int(child.text)
    grandchild = handler.post('/artifact/split', {'p_id': 1, 'parent_id': child_id, 'identifier': identifier,
                                                  'start': 0, 'end': 5, 'data': data[0:5]}, True)
    assert grandchild.status_code == 200
    grandchild_id = int(grandchild.text)

    response = handler.post('/artifact/delete', {'p_id': 1, 'a_ids': [2]}, True)
    assert response.status_code == 200
    assert response.json['deleted'] == sorted([2, child_id, grandchild_id])
    with app.app_context():
        for a_id in (2, child_id, grandchild_id):
            assert db.session.get(Artifact, a_id) is None


def test_delete_artifact_validation(app, client):
    handler = RequestHandler(app, client, 2)
    # Not an admin of project 1
    assert RequestHandler(app, client, 6).post(
        '/artifact/delete', {'p_id': 1, 'a_ids': [1]}, True).status_code == 401
    # Artifact of another project
    with app.app_context():
        other = db.session.scalar(select(Artifact.id).where(Artifact.p_id != 1))
    assert handler.post('/artifact/delete', {'p_id': 1, 'a_ids': [other]}, True).status_code == 400
    assert _count(app, select(func.count()).select_from(Artifact).where(Artifact.id == other)) == 1
    # Bad input
    assert handler.post('/artifact/delete', {'p_id': 1, 'a_ids': []}, True).status_code == 400
    assert handler.post('/artifact/delete', {'p_id': 1, 'a_ids': ['x']}, True).status_code == 400
    assert handler.post('/artifact/delete', {'p_id': 1}, True).status_code == 400
