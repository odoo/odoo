from odoo.tools.module_data import rename_module


def migrate(cr, version):
    if not version:
        return
    rename_module(cr, "fleet_vehicle_verification", "l10n_mx_fleet_emission")
