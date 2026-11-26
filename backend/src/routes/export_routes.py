"""
Routes for exporting the labelling results of a project, so that they can be
analysed outside of LaMa (spreadsheet, R, pandas, ...) without querying the database.
"""

import csv
import io
from collections import defaultdict

from flask import Blueprint, jsonify, make_response, request
from sqlalchemy import select

from src.app_util import in_project, login_required
from src.models import db
from src.models.auth_models import User
from src.models.item_models import Artifact, Label, LabelType, Labelling, Theme, label_to_theme

export_routes = Blueprint("export", __name__, url_prefix="/export")

# Columns of the labelling export, in order
LABELLING_COLUMNS = [
    "artifact_id",
    "artifact_identifier",
    "artifact_text",
    "parent_artifact_id",
    "label_type",
    "label",
    "label_description",
    "themes",
    "labeller",
    "remark",
    "labelling_time",
]

# Characters that make spreadsheet programs interpret a cell as a formula
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _csv_safe(value):
    """
    Protects against CSV/formula injection when the file is opened in a spreadsheet
    program, by prefixing cells that start with a formula character with a quote.
    See https://owasp.org/www-community/attacks/CSV_Injection
    (The JSON export contains the unmodified values.)
    """
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def get_labelling_rows(p_id, u_id=None):
    """
    Gets one row per labelling (artifact x label type x labeller) of a project.
    @param p_id : the id of the project
    @param u_id : if given, only the labellings made by this user are returned
    @return a list of dictionaries with the keys in LABELLING_COLUMNS
    """
    # Themes (that are not deleted) each label belongs to
    theme_rows = db.session.execute(
        select(label_to_theme.c.l_id, Theme.name)
        .join(Theme, Theme.id == label_to_theme.c.t_id)
        .where(Theme.p_id == p_id, Theme.deleted == False)  # noqa: E712
        .order_by(Theme.name)
    ).all()
    themes_per_label = defaultdict(list)
    for l_id, theme_name in theme_rows:
        themes_per_label[l_id].append(theme_name)

    query = (
        select(
            Artifact.id,
            Artifact.identifier,
            Artifact.data,
            Artifact.parent_id,
            LabelType.name,
            Label.id,
            Label.name,
            Label.description,
            User.username,
            Labelling.remark,
            Labelling.time,
        )
        .select_from(Labelling)
        .join(Artifact, Artifact.id == Labelling.a_id)
        .join(Label, Label.id == Labelling.l_id)
        .join(LabelType, LabelType.id == Labelling.lt_id)
        .join(User, User.id == Labelling.u_id)
        .where(Labelling.p_id == p_id)
        .order_by(Artifact.id, LabelType.id, User.username)
    )
    if u_id is not None:
        query = query.where(Labelling.u_id == u_id)

    rows = []
    for (a_id, identifier, data, parent_id, lt_name, l_id, l_name, l_description,
         username, remark, time) in db.session.execute(query):
        rows.append({
            "artifact_id": a_id,
            "artifact_identifier": identifier,
            "artifact_text": data,
            "parent_artifact_id": parent_id,
            "label_type": lt_name,
            "label": l_name,
            "label_description": l_description,
            "themes": "; ".join(themes_per_label.get(l_id, [])),
            "labeller": username,
            "remark": remark,
            "labelling_time": time.isoformat() if time is not None else None,
        })
    return rows


def rows_to_csv(rows, columns):
    """
    Serializes rows (dictionaries) to CSV.
    Starts with a UTF-8 byte order mark so that Excel detects the encoding correctly.
    """
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _csv_safe(value) for key, value in row.items()})
    return "﻿" + buffer.getvalue()


@export_routes.route("/labellings", methods=["GET"])
@login_required
@in_project
def export_labellings(*, user, membership):
    """
    Exports the labellings of a project.
    Project admins export the labellings of every user, other members only their own.
    @param p_id : id of the project (query parameter)
    @param format : "csv" (default) or "json" (query parameter)
    """
    p_id = request.args.get("p_id", type=int)
    export_format = request.args.get("format", "csv").lower()
    if p_id is None or export_format not in ("csv", "json"):
        return make_response("Bad Request", 400)

    rows = get_labelling_rows(p_id, None if membership.admin else user.id)

    if export_format == "json":
        return jsonify(rows)

    response = make_response(rows_to_csv(rows, LABELLING_COLUMNS))
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = f'attachment; filename="lama_project_{p_id}_labellings.csv"'
    return response
