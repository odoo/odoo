from odoo.db.schema import table_exists
from odoo.tools.module_data import remove_xmlid_records

ROOM_MODELS = ("room.room", "room.booking", "room.office")
PARKED = "__retired_room__"
RETIRED_RULES = (
    "room_room_comp_rule",
    "room_office_comp_rule",
    "room_booking_comp_rule",
)


def migrate(cr, version):
    if not version or not table_exists(cr, "room_room"):
        return
    _drop_room_views(cr)
    remove_xmlid_records(cr, "room", RETIRED_RULES)
    cr.execute("DELETE FROM ir_filters WHERE model_id = ANY(%s)", [list(ROOM_MODELS)])
    cr.execute(
        """
        UPDATE ir_model_data
           SET name = module || '.' || name, module = %s
         WHERE model = ANY(%s) AND module != %s
        """,
        [PARKED, list(ROOM_MODELS), PARKED],
    )


def _drop_room_views(cr):
    cr.execute(
        """
        WITH RECURSIVE doomed AS (
            SELECT id FROM ir_ui_view WHERE model = ANY(%s)
             UNION
            SELECT view.id FROM ir_ui_view view JOIN doomed ON view.inherit_id = doomed.id
        )
        SELECT array_agg(id) FROM doomed
        """,
        [list(ROOM_MODELS)],
    )
    view_ids = cr.fetchone()[0] or []
    if not view_ids:
        return
    cr.execute("DELETE FROM ir_act_window_view WHERE view_id = ANY(%s)", [view_ids])
    cr.execute(
        "DELETE FROM ir_model_data WHERE model = 'ir.ui.view' AND res_id = ANY(%s)",
        [view_ids],
    )
    cr.execute(
        "UPDATE ir_ui_view SET inherit_id = NULL, mode = 'primary' WHERE id = ANY(%s)",
        [view_ids],
    )
    cr.execute("DELETE FROM ir_ui_view WHERE id = ANY(%s)", [view_ids])
