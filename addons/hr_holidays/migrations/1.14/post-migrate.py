def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        DELETE FROM resource_reservation reservation
              USING calendar_event event
               JOIN ir_model origin ON origin.id = event.res_model_id
              WHERE reservation.res_model = 'calendar.event'
                AND reservation.res_id = event.id
                AND origin.model = 'hr.leave'
        """
    )
