import csv
import io

from sqlalchemy import func, select

from src.conftest import RequestHandler
from src.models import db
from src.models.item_models import Labelling
from src.routes.export_routes import LABELLING_COLUMNS, _csv_safe


def _parse_csv(response):
    text = response.get_data(as_text=True)
    # The export starts with a byte order mark for Excel
    assert text.startswith("﻿")
    return list(csv.DictReader(io.StringIO(text[1:])))


def test_export_requires_login(app, client):
    response = RequestHandler(app, client).get('/export/labellings', {'p_id': 1}, False)
    assert response.status_code == 401


def test_export_requires_membership(app, client):
    # User 2 is not a member of project 4
    response = RequestHandler(app, client, 2).get('/export/labellings', {'p_id': 4}, True)
    assert response.status_code == 401


def test_export_bad_format(app, client):
    response = RequestHandler(app, client, 2).get('/export/labellings', {'p_id': 1, 'format': 'xml'}, True)
    assert response.status_code == 400


def test_export_admin_gets_all_labellings_csv(app, client):
    # User 2 is an admin of project 1
    response = RequestHandler(app, client, 2).get('/export/labellings', {'p_id': 1}, True)
    assert response.status_code == 200
    assert response.headers['Content-Type'].startswith('text/csv')
    assert 'attachment' in response.headers['Content-Disposition']

    rows = _parse_csv(response)
    with app.app_context():
        expected = db.session.scalar(select(func.count()).select_from(Labelling).where(Labelling.p_id == 1))
    assert expected > 0
    assert len(rows) == expected
    assert list(rows[0].keys()) == LABELLING_COLUMNS
    # More than one labeller is included
    assert len({row['labeller'] for row in rows}) > 1


def test_export_non_admin_gets_own_labellings_json(app, client):
    # User 6 is a member, but not an admin, of project 1
    response = RequestHandler(app, client, 6).get('/export/labellings', {'p_id': 1, 'format': 'json'}, True)
    assert response.status_code == 200

    with app.app_context():
        expected = db.session.scalar(
            select(func.count()).select_from(Labelling).where(Labelling.p_id == 1, Labelling.u_id == 6))
        username = db.session.scalar(select(Labelling).where(Labelling.u_id == 6)).user.username
    assert len(response.json) == expected
    assert {row['labeller'] for row in response.json} == {username}


def test_csv_safe():
    assert _csv_safe("=SUM(A1)") == "'=SUM(A1)"
    assert _csv_safe("-1") == "'-1"
    assert _csv_safe("normal text") == "normal text"
    assert _csv_safe(5) == 5
    assert _csv_safe(None) is None
