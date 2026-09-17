def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "UPDATE maintenance_order SET date_confirmed = NULL WHERE state = 'draft'"
    )
    # Draft leads only to confirmed or cancelled, so an order past draft was confirmed by
    # its first tracked state change, unless it was cancelled and redrafted before.
    cr.execute(
        """
        WITH first_change AS (
            SELECT DISTINCT ON (message.res_id)
                   message.res_id AS order_id, message.date
              FROM mail_tracking_value tracking
              JOIN mail_message message ON message.id = tracking.mail_message_id
              JOIN ir_model_fields field ON field.id = tracking.field_id
             WHERE field.model = 'maintenance.order'
               AND field.name = 'state'
               AND message.model = 'maintenance.order'
          ORDER BY message.res_id, message.date, message.id
        )
        UPDATE maintenance_order o
           SET date_confirmed = date_trunc(
                   'second', COALESCE(first_change.date, o.create_date)
               )
          FROM maintenance_order source
     LEFT JOIN first_change ON first_change.order_id = source.id
         WHERE source.id = o.id
           AND o.state IN ('confirmed', 'in_progress', 'done')
        """
    )
