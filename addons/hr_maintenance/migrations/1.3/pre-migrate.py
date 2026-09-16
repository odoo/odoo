from odoo.tools.module_data import adopt_xmlids

MOVED = (
    "hr_employee_view_form",
    "hr_departure_wizard_view_form",
    "resource_asset_view_form_inherit_hr",
)


def migrate(cr, version):
    if not version:
        return
    # Employee custody is hr + resource_asset; it only ever lived here because
    # equipment did. The records move with the code.
    cr.execute(
        """
        UPDATE ir_module_module
           SET state = 'to install'
         WHERE name = 'resource_asset_hr'
           AND state = 'uninstalled'
        """
    )
    adopt_xmlids(cr, "hr_maintenance", "resource_asset_hr", MOVED)
