from odoo.db import schema

from odoo.addons.resource_asset.table_inheritance import land_set_aside_columns

COLUMNS = (
    "l10n_mx_emission_plate_digit",
    "l10n_mx_emission_calendar_id",
    "l10n_mx_emission_color",
)


def migrate(cr, version):
    land_set_aside_columns(
        cr, "resource_asset_vehicle", COLUMNS, "l10n_mx_fleet_emission 2.1"
    )
    schema.drop_columns(
        cr,
        "l10n_mx_fleet_emission_inspection",
        ["company_id", "calendar_id", "sticker_color", "color_sequence"],
    )
