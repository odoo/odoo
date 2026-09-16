from odoo.db.schema import column_exists, table_exists
from odoo.tools.module_data import rename_field, rename_model

MODELS = {
    "fleet.vehicle.verification.calendar": "l10n_mx.fleet.emission.calendar",
    "fleet.vehicle.verification": "l10n_mx.fleet.emission.inspection",
}
INSPECTION_FIELDS = {
    "semester": "period",
    "verification_color": "sticker_color",
    "scheduled_date": "date_scheduled",
    "done_date": "date_done",
    "certificate": "certificate_number",
}
CALENDAR_XMLIDS = ("yellow", "pink", "red", "green", "blue")


def migrate(cr, version):
    if not version or not table_exists(cr, "fleet_vehicle_verification_calendar"):
        return
    # The retired views name fields that no longer exist; the new files recreate them.
    cr.execute(
        "DELETE FROM ir_ui_view WHERE model = ANY(%s)",
        [list(MODELS)],
    )
    for old, new in MODELS.items():
        rename_model(cr, old, new)
    for old, new in INSPECTION_FIELDS.items():
        rename_field(cr, "l10n_mx.fleet.emission.inspection", old, new)
    if column_exists(cr, "l10n_mx_fleet_emission_inspection", "vehicle_id"):
        cr.execute(
            """
            ALTER TABLE l10n_mx_fleet_emission_inspection
            RENAME COLUMN vehicle_id TO legacy_vehicle_id
            """
        )
        cr.execute(
            """
            ALTER TABLE l10n_mx_fleet_emission_inspection
            ALTER COLUMN legacy_vehicle_id DROP NOT NULL
            """
        )
    cr.execute(
        """
        UPDATE ir_model_data
           SET name = 'emission_calendar_' || substr(name, 23)
         WHERE module = 'l10n_mx_fleet_emission'
           AND name = ANY(%s)
        """,
        [[f"verification_calendar_{color}" for color in CALENDAR_XMLIDS]],
    )
