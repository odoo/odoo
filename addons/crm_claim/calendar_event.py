# -*- coding: utf-8 -*-

from openerp import fields, models


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    claim_id = fields.Many2one('crm.claim', string="Claim", ondelete='cascade')
