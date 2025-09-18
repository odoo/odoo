"""Helper functions for the /json route controller.

Provides ``get_view_id_and_type``, ``get_default_domain``,
``get_date_domain``, and ``get_groupby`` — view/domain resolution logic
consumed by ``WebJsonController`` in ``json.py``.
"""

import ast
import re
from collections import defaultdict
from datetime import date

from dateutil.relativedelta import relativedelta
from lxml import etree
from werkzeug.exceptions import BadRequest

from odoo.fields import Domain
from odoo.http import request
from odoo.models import check_object_name
from odoo.tools.safe_eval import safe_eval


def get_view_id_and_type(action, view_type: str | None) -> tuple[int | None, str]:
    """Extract the view id and type from *action*."""
    if action._name != "ir.actions.act_window":
        msg = f"Expected ir.actions.act_window, got {action._name}"
        raise TypeError(msg)
    view_modes = action.view_mode.split(",")
    if not view_type:
        view_type = view_modes[0]

    try:
        view_id = next(
            view_id
            for view_id, action_view_type in action.views
            if view_type == action_view_type
        )
    except StopIteration:
        if view_type not in view_modes:
            raise BadRequest(
                request.env._(
                    "Invalid view type '%(view_type)s' for action id=%(action)s",
                    view_type=view_type,
                    action=action.id,
                )
            ) from None
        view_id = False
    return view_id, view_type


def get_default_domain(model, action, context, eval_context):
    """Build the default domain from user filters or search defaults."""
    for ir_filter in model.env["ir.filters"].get_filters(
        model._name, action._origin.id
    ):
        if ir_filter["is_default"]:
            # user filters, static parsing only
            domain_str = ir_filter["domain"]
            domain_str = re.sub(r"\buid\b", str(model.env.uid), domain_str)
            default_domain = ast.literal_eval(domain_str)
            break
    else:

        def filters_from_context():
            view_tree = None
            for key, value in context.items():
                if key.startswith("search_default_") and value:
                    filter_name = key[15:]
                    if not check_object_name(filter_name):
                        raise ValueError(
                            model.env._(
                                "Invalid default search filter name for %s", key
                            )
                        )
                    if view_tree is None:
                        view = model.get_view(action.search_view_id.id, "search")
                        view_tree = etree.fromstring(view["arch"])
                    if (
                        element := next(
                            (
                                el
                                for el in view_tree.iterfind(".//filter")
                                if el.get("name") == filter_name
                            ),
                            None,
                        )
                    ) is not None:
                        # parse the domain
                        if domain := element.attrib.get("domain"):
                            yield domain
                        # not parsing context['group_by']

        default_domain = Domain.AND(
            safe_eval(domain, eval_context) for domain in filters_from_context()
        )
    return default_domain


def get_date_domain(start_date, end_date, view_tree):
    """Build a date-range domain for calendar/gantt/cohort views."""
    if not start_date or not end_date:
        start_date = date.today() + relativedelta(day=1)
        end_date = start_date + relativedelta(months=1)
    date_field = view_tree.attrib.get("date_start")
    if not date_field:
        msg = "Could not find the date field in the view"
        raise ValueError(msg)
    return [(date_field, ">=", start_date), (date_field, "<", end_date)]


def get_groupby(view_tree, groupby=None, fields=None):
    """Parse the given groupby and fields, falling back to the view definition.

    Return the groupby as a list when given.  Otherwise find groupby and
    fields from the view.

    :param view_tree: The xml tree of the view
    :param groupby: string or None
    :param fields: string or None
    """
    if groupby:
        groupby = groupby.split(",")
    if fields:
        fields = fields.split(",")
    else:
        fields = None
    if groupby is not None:
        return groupby, fields

    if view_tree.tag in ("pivot", "graph"):
        # extract groupby from the view if we don't have any
        field_by_type = defaultdict(list)
        for element in view_tree.findall(r"./field"):
            field_name = element.attrib.get("name")
            if element.attrib.get("invisible", "") in ("1", "true"):
                field_by_type["invisible"].append(field_name)
            else:
                field_by_type[element.attrib.get("type", "normal")].append(field_name)
            # not reading interval from the attribute
        groupby = [
            *field_by_type.get("row", ()),
            *field_by_type.get("col", ()),
            *field_by_type.get("normal", ()),
        ]
        if fields is None:
            fields = field_by_type.get("measure", [])
        return groupby, fields
    if view_tree.attrib.get("default_group_by"):
        # in case the kanban view (or other) defines a default grouping
        # return the field name so it is added to the spec
        field = view_tree.attrib.get("default_group_by")
        return (None, [field] if field else [])
    return None, None
