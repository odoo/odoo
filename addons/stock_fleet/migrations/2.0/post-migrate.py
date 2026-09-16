from odoo.db.schema import column_exists, table_exists


def migrate(cr, version):
    if not version or not table_exists(cr, "fleet_migration_map"):
        return
    if column_exists(cr, "stock_picking_batch", "legacy_vehicle_id"):
        cr.execute(
            """
            UPDATE stock_picking_batch batch
               SET vehicle_id = map.new_id
              FROM fleet_migration_map map
             WHERE map.model = 'fleet.vehicle'
               AND map.old_id = batch.legacy_vehicle_id
            """
        )
        cr.execute("ALTER TABLE stock_picking_batch DROP COLUMN legacy_vehicle_id")
        cr.execute(
            """
            UPDATE stock_picking_batch batch
               SET vehicle_model_id = asset.product_id
              FROM resource_asset asset
             WHERE asset.id = batch.vehicle_id
            """
        )
    if column_exists(cr, "fleet_vehicle_model_category", "weight_capacity"):
        cr.execute(
            """
            UPDATE product_template template
               SET weight_capacity = category.weight_capacity,
                   volume_capacity = category.volume_capacity
              FROM product_product product
              JOIN fleet_migration_map model_map
                ON model_map.model = 'fleet.vehicle.model'
               AND model_map.new_id = product.id
              JOIN fleet_vehicle_model model ON model.id = model_map.old_id
              JOIN fleet_vehicle_model_category category ON category.id = model.category_id
             WHERE template.id = product.product_tmpl_id
               AND COALESCE(template.weight_capacity, 0) = 0
            """
        )
