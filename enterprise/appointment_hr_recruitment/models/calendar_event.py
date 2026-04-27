# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _

class CalendarEventRecruitment(models.Model):
    _inherit = 'calendar.event'

    applicant_id = fields.Many2one(related="appointment_invite_id.applicant_id", readonly=False, store=True)
