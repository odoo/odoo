from odoo.db import schema


def migrate(cr, version):
    if not version:
        return
    schema.drop_columns(cr, "l10n_mx_fleet_emission_inspection", ["company_id", "calendar_id", "sticker_color", "color_sequence"])
    schema.drop_columns(cr, "resource_asset", ["l10n_mx_emission_color"])
