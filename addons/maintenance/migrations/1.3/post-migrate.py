def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE maintenance_order
           SET date_occurrence = schedule_date
         WHERE plan_id IS NOT NULL
           AND date_occurrence IS NULL
        """
    )
