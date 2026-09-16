from odoo.db.schema import column_exists, table_exists


def migrate(cr, version):
    if not version or not table_exists(cr, "fleet_migration_map"):
        return
    if column_exists(cr, "account_move_line", "vehicle_id"):
        cr.execute(
            """
            UPDATE account_move_line line
               SET asset_id = map.new_id
              FROM fleet_migration_map map
             WHERE map.model = 'fleet.vehicle'
               AND map.old_id = line.vehicle_id
               AND line.asset_id IS NULL
            """
        )
        cr.execute("ALTER TABLE account_move_line DROP COLUMN vehicle_id")
    if column_exists(cr, "fleet_vehicle_log_services", "account_move_line_id"):
        cr.execute(
            """
            UPDATE resource_asset_log log
               SET account_move_line_id = service.account_move_line_id,
                   source = 'bill'
              FROM fleet_vehicle_log_services service
              JOIN fleet_migration_map map
                ON map.model = 'fleet.vehicle.log.services' AND map.old_id = service.id
             WHERE log.id = map.new_id
               AND service.account_move_line_id IS NOT NULL
               AND NOT EXISTS (
                   SELECT 1 FROM resource_asset_log other
                    WHERE other.account_move_line_id = service.account_move_line_id
               )
            """
        )
