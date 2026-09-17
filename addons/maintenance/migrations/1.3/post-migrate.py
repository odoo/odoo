def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE maintenance_order
           SET date_plan_slot = date_scheduled_start
         WHERE plan_id IS NOT NULL
           AND date_plan_slot IS NULL
        """
    )
