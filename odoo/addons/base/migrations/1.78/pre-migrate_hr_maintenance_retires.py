from odoo.db.schema import column_exists
from odoo.tools.module_data import remove_xmlid_records, retire_empty_module

MODULE = "hr_maintenance"


def migrate(cr, version):
    if not version:
        return
    cr.execute("SELECT id, state FROM ir_module_module WHERE name = %s", [MODULE])
    row = cr.fetchone()
    if not row:
        return
    module_id, state = row
    if state != "uninstalled":
        # A maintenance order names users, like a sale, purchase or invoice does;
        # the employee who raised it goes with the module that added it.
        cr.execute("SELECT name FROM ir_model_data WHERE module = %s", [MODULE])
        remove_xmlid_records(cr, MODULE, [name for (name,) in cr.fetchall()])
        cr.execute("DELETE FROM ir_model_constraint WHERE module = %s", [module_id])
        cr.execute("DELETE FROM ir_model_relation WHERE module = %s", [module_id])
        if column_exists(cr, "maintenance_order", "employee_id"):
            cr.execute("ALTER TABLE maintenance_order DROP COLUMN employee_id")
        cr.execute(
            """
            DELETE FROM res_groups_implied_rel rel
             USING ir_model_data hr_user, ir_model_data manager
             WHERE hr_user.module = 'hr' AND hr_user.name = 'group_hr_user'
               AND manager.module = 'maintenance'
               AND manager.name = 'group_equipment_manager'
               AND rel.gid = hr_user.res_id AND rel.hid = manager.res_id
            """
        )
    retire_empty_module(cr, MODULE)
