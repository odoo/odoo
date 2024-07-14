# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AppointmentType(models.Model):
    _inherit = "appointment.type"

    def _populate(self, size):
        appointment_types = super()._populate(size)
        appointment_types.is_published = True
        return appointment_types
