def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE maintenance_plan plan
           SET asset_id = request.asset_id,
               block_asset = request.block_asset
          FROM maintenance_order request
         WHERE request.plan_id = plan.id
           AND request.asset_id IS NOT NULL
           AND plan.asset_id IS NULL
        """
    )
