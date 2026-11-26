# Author: Victoria
# Author: Bartjan
# Author: Eduardo Costa Martins
from src.app_util import check_args, check_string, check_whitespaces
# Need this in every route
from src import db
from flask import make_response, request, Blueprint, jsonify
from sqlalchemy import select, func, delete, update
from sqlalchemy.exc import OperationalError, IntegrityError
from src.app_util import login_required, in_project, not_frozen
from src.models.item_models import Label, LabelType, Labelling, label_to_theme
from collections import defaultdict

label_type_routes = Blueprint("labeltype", __name__, url_prefix="/labeltype")

# Author: B. Henkemans
# Gets label types
@label_type_routes.route('/all', methods=['GET'])
@login_required
@in_project
def get_label_types():
    # Get args from request
    args = request.args
    # What args are required
    required = ['p_id']

    # Check if required args are present
    if not check_args(required, args):
        return make_response('Bad Request', 400)

    # Get all the labels of a labelType
    label_types = db.session.execute(
        select(LabelType)
        .where(LabelType.p_id == args['p_id'])
    ).scalars().all()

    # Initialise label type schema
    label_type_schema = LabelType.__marshmallow__()
    # Jsonify label type schema
    label_type_json = jsonify(label_type_schema.dump(label_types, many=True))

    return make_response(label_type_json)

# Author: B. Henkemans
# Gets label types with labels
@label_type_routes.route('/allWithLabels', methods=['GET'])
@login_required
@in_project
def get_label_types_wl():
    # Get args from request
    args = request.args
    # What args are required
    required = ['p_id']

    # Check if required args are present
    if not check_args(required, args):
        return make_response('Bad Request', 400)

    # Get all the labels of a labelType
    labelTypes = db.session.scalars(
        select(LabelType)
        .where(
            LabelType.p_id == args['p_id']
        )
    ).all()

    # Initialise label type schema
    label_type_schema = LabelType.__marshmallow__()
    # Initialise label schema
    label_schema = Label.__marshmallow__()

    # Create dictionary with label type and labels
    dict_json = jsonify([{
        'label_type': label_type_schema.dump(labelType),
        'labels': label_schema.dump((labelType.labels).filter_by(deleted=0), many=True)
    } for labelType in labelTypes])

    return make_response(dict_json)

# Author: Eduardo Costa Martins
# Get labels by label type
@label_type_routes.route("/labelsByType", methods=["GET"])
@login_required
@in_project
def get_labels_by_label_type():
    # Get args from request
    args = request.args
    # What args are required
    required = ['p_id', 'lt_id']

    # Check if required args are present
    if not check_args(required, args):
        return make_response('Bad Request', 400)

    # Check if the label type is part of the project
    lt = db.session.scalars(select(LabelType).where(
        LabelType.p_id == args['p_id'], 
        LabelType.id == args['lt_id'])).all()
    if not lt:
        return make_response('Label type does not exist in this project', 400)
        
    # Get all the labels of a labelType
    labelType = db.session.scalar(
        select(LabelType)
        .where(
            LabelType.id == args['lt_id']
        )
    )

    # Initialise label schema
    label_schema = Label.__marshmallow__()

    # Create dictionary with label type and labels
    dict_json = label_schema.dump(
        (labelType.labels).filter_by(deleted=0), many=True)
    return make_response(jsonify(dict_json))


"""
Author: Eduardo Costa Martins
@params p_id : int|string the project id for which you want the label types and labels
@returns a dictionary indexed by label type _objects_, mapping to a list of labels of that type
"""
def labels_by_label_type(p_id):
    # Get labels by label type
    stmt = select(
        LabelType, Label
    ).where(
        Label.lt_id == LabelType.id,
        LabelType.p_id == p_id
    )
    # Get the results
    results = db.session.execute(stmt).all()

    # Group the results
    grouped_results = defaultdict(list)
    for k, v in results:
        grouped_results[k].append(v)

    return grouped_results


"""
Label type management after project creation (project admins only).
Changes are applied immediately, they are not part of the project settings "Save".
"""

def __validate_label_type_name(name):
    """Returns an error response if the name is not a valid label type name, None otherwise."""
    if not isinstance(name, str) or not name.strip():
        return make_response('Label type name cannot be empty', 400)
    if check_whitespaces([name]):
        return make_response('Input contains leading or trailing whitespaces', 400)
    if check_string([name]):
        return make_response('Input contains a forbidden character', 511)
    if len(name) > 64:
        return make_response('Label type name is too long (max 64 characters)', 400)
    return None


def __name_taken(p_id, name, exclude_id=None):
    stmt = select(LabelType.id).where(LabelType.p_id == p_id, LabelType.name == name)
    if exclude_id is not None:
        stmt = stmt.where(LabelType.id != exclude_id)
    return db.session.scalar(stmt) is not None


def __get_project_label_type(p_id, lt_id):
    return db.session.scalar(select(LabelType).where(LabelType.p_id == p_id, LabelType.id == lt_id))


# Creates a new label type in an existing project
@label_type_routes.route('/create', methods=['POST'])
@login_required
@in_project
@not_frozen
def create_label_type(*, membership):
    if not membership.admin:
        return make_response('Only project admins can add label types', 401)

    args = request.json
    if not check_args(['p_id', 'name'], args):
        return make_response('Bad Request', 400)

    error = __validate_label_type_name(args['name'])
    if error:
        return error
    if __name_taken(args['p_id'], args['name']):
        return make_response('A label type with this name already exists', 400)

    label_type = LabelType(p_id=args['p_id'], name=args['name'])
    db.session.add(label_type)
    try:
        db.session.commit()
    except (OperationalError, IntegrityError):
        db.session.rollback()
        return make_response('Internal Server Error', 503)

    return make_response(jsonify(LabelType.__marshmallow__().dump(label_type)), 201)


# Renames a label type
@label_type_routes.route('/rename', methods=['PATCH'])
@login_required
@in_project
@not_frozen
def rename_label_type(*, membership):
    if not membership.admin:
        return make_response('Only project admins can rename label types', 401)

    args = request.json
    if not check_args(['p_id', 'lt_id', 'name'], args):
        return make_response('Bad Request', 400)

    label_type = __get_project_label_type(args['p_id'], args['lt_id'])
    if label_type is None:
        return make_response('Label type does not exist in this project', 400)

    error = __validate_label_type_name(args['name'])
    if error:
        return error
    if __name_taken(args['p_id'], args['name'], exclude_id=label_type.id):
        return make_response('A label type with this name already exists', 400)

    label_type.name = args['name']
    try:
        db.session.commit()
    except (OperationalError, IntegrityError):
        db.session.rollback()
        return make_response('Internal Server Error', 503)

    return make_response(jsonify(LabelType.__marshmallow__().dump(label_type)), 200)


"""
Deletes a label type, together with all its labels and every labelling that used them.
This cannot be undone. A project always keeps at least one label type.
"""
@label_type_routes.route('/delete', methods=['POST'])
@login_required
@in_project
@not_frozen
def delete_label_type(*, membership):
    if not membership.admin:
        return make_response('Only project admins can delete label types', 401)

    args = request.json
    if not check_args(['p_id', 'lt_id'], args):
        return make_response('Bad Request', 400)

    p_id = args['p_id']
    label_type = __get_project_label_type(p_id, args['lt_id'])
    if label_type is None:
        return make_response('Label type does not exist in this project', 400)

    n_label_types = db.session.scalar(select(func.count(LabelType.id)).where(LabelType.p_id == p_id))
    if n_label_types <= 1:
        return make_response('A project needs at least one label type', 400)

    lt_id = label_type.id
    label_ids = select(Label.id).where(Label.p_id == p_id, Label.lt_id == lt_id)
    LabelChange = Label.__change__

    try:
        # Labellings of this type
        db.session.execute(delete(Labelling).where(Labelling.p_id == p_id, Labelling.lt_id == lt_id)
                           .execution_options(synchronize_session=False))
        # Theme assignments of the labels
        db.session.execute(delete(label_to_theme).where(label_to_theme.c.l_id.in_(label_ids)))
        # Labels (of other types) that were merged into one of these labels
        db.session.execute(update(Label).where(Label.child_id.in_(label_ids), Label.lt_id != lt_id)
                           .values(child_id=None).execution_options(synchronize_session=False))
        # Merge references among the labels themselves, so they can be deleted in any order
        db.session.execute(update(Label).where(Label.p_id == p_id, Label.lt_id == lt_id)
                           .values(child_id=None).execution_options(synchronize_session=False))
        # Change history of the labels
        db.session.execute(delete(LabelChange).where(LabelChange.i_id.in_(label_ids))
                           .execution_options(synchronize_session=False))
        # The labels and the label type itself
        db.session.execute(delete(Label).where(Label.p_id == p_id, Label.lt_id == lt_id)
                           .execution_options(synchronize_session=False))
        db.session.execute(delete(LabelType).where(LabelType.id == lt_id)
                           .execution_options(synchronize_session=False))
        db.session.commit()
    except (OperationalError, IntegrityError):
        db.session.rollback()
        return make_response('Internal Server Error', 503)

    return make_response('Label type deleted', 200)
