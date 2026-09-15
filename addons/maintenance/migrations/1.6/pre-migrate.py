from odoo.db.schema import table_exists
from odoo.tools.module_data import remove_xmlid_records

EQUIPMENT_MODELS = ("maintenance.equipment", "maintenance.equipment.category")
PARKED = "__retired_equipment__"
RETIRED_RULES = (
    "equipment_rule_user",
    "equipment_rule_admin_user",
    "maintenance_equipment_comp_rule",
    "maintenance_equipment_category_comp_rule",
)


def migrate(cr, version):
    if not version or not table_exists(cr, "maintenance_equipment"):
        return
    _drop_equipment_views(cr)
    remove_xmlid_records(cr, "maintenance", RETIRED_RULES)
    _park_xmlids(cr)


def _drop_equipment_views(cr):
    cr.execute(
        """
        WITH RECURSIVE doomed AS (
            SELECT id FROM ir_ui_view WHERE model = ANY(%s)
             UNION
            SELECT view.id FROM ir_ui_view view JOIN doomed ON view.inherit_id = doomed.id
        )
        SELECT array_agg(id) FROM doomed
        """,
        [list(EQUIPMENT_MODELS)],
    )
    view_ids = cr.fetchone()[0] or []
    if not view_ids:
        return
    cr.execute(
        "DELETE FROM ir_model_data WHERE model = 'ir.ui.view' AND res_id = ANY(%s)",
        [view_ids],
    )
    cr.execute(
        "UPDATE ir_ui_view SET inherit_id = NULL, mode = 'primary' WHERE id = ANY(%s)",
        [view_ids],
    )
    cr.execute("DELETE FROM ir_ui_view WHERE id = ANY(%s)", [view_ids])


def _park_xmlids(cr):
    cr.execute(
        """
        UPDATE ir_model_data
           SET name = module || '.' || name, module = %s
         WHERE model = ANY(%s) AND module != %s
        """,
        [PARKED, list(EQUIPMENT_MODELS), PARKED],
    )
