from odoo.addons.appointment.controllers.calendar import AppointmentCalendarController


class AppointmentAccountPaymentCalendarController(AppointmentCalendarController):

    def _get_prevent_cancel_status(self, event):
        if event.appointment_type_id.has_payment_step:
            return 'no_cancel_paid'
        return super()._get_prevent_cancel_status(event)
