from odoo.addons.resource_asset.table_inheritance import set_aside_root_columns

COLUMNS = (
    "l10n_mx_emission_plate_digit",
    "l10n_mx_emission_calendar_id",
    "l10n_mx_emission_color",
)


def migrate(cr, version):
    set_aside_root_columns(cr, COLUMNS)
