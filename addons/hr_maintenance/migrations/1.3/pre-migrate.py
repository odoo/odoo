from odoo.tools.module_data import remove_xmlid_records

MOVED = (
    "hr_employee_view_form",
    "hr_departure_wizard_view_form",
    "resource_asset_view_form_inherit_hr",
)


def migrate(cr, version):
    if not version:
        return
    # Employee custody is hr + resource_asset; it only ever lived here because
    # equipment did. `resource_asset_hr` loads first and declares its own views
    # under the same names, so these are dropped rather than handed over: an
    # adoption would collide on (module, name).
    cr.execute(
        """
        UPDATE ir_module_module
           SET state = 'to install'
         WHERE name = 'resource_asset_hr'
           AND state = 'uninstalled'
        """
    )
    remove_xmlid_records(cr, "hr_maintenance", MOVED)
