# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AppointmentType(models.Model):
    _inherit = "appointment.type"

    @api.model
    def _get_calendar_view_appointment_type_default_context_fields_whitelist(self):
        """ Add the applicant_id field to list of fields we accept as default in context """
        whitelist_fields = super()._get_calendar_view_appointment_type_default_context_fields_whitelist()
        whitelist_fields.append('applicant_id')
        return whitelist_fields
