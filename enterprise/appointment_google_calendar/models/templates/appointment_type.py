from odoo import models


class AppointmentType(models.Model):
    _inherit = 'appointment.type'

    def _get_default_template_videocall_source(self):
        return 'google_meet'
