from odoo.db.schema import column_exists, table_exists


def migrate(cr, version):
    if not version or not column_exists(
        cr, "l10n_mx_fleet_emission_inspection", "legacy_vehicle_id"
    ):
        return
    if table_exists(cr, "fleet_migration_map"):
        cr.execute(
            """
            UPDATE l10n_mx_fleet_emission_inspection inspection
               SET asset_id = map.new_id
              FROM fleet_migration_map map
             WHERE map.model = 'fleet.vehicle'
               AND map.old_id = inspection.legacy_vehicle_id
            """
        )
    cr.execute("DELETE FROM l10n_mx_fleet_emission_inspection WHERE asset_id IS NULL")
    cr.execute(
        "ALTER TABLE l10n_mx_fleet_emission_inspection DROP COLUMN legacy_vehicle_id"
    )
