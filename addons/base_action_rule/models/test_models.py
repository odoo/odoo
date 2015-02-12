# -*- coding: utf-8 -*-
from openerp import models, fields

AVAILABLE_STATES = [
    ('draft', 'New'),
    ('cancel', 'Cancelled'),
    ('open', 'In Progress'),
    ('pending', 'Pending'),
    ('done', 'Closed')
]


class LeadTest(models.Model):
    _name = "base.action.rule.lead.test"

    name = fields.Char(string='Subject', required=True, index=True)
    user_id = fields.Many2one('res.users', string='Responsible')
    state = fields.Selection(AVAILABLE_STATES, string="Status", default="draft", readonly=True)
    active = fields.Boolean(default=True)
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='set null')
    date_action_last = fields.Datetime(string='Last Action', readonly=1)

    def message_post(self, body='', subject=None, type='notification', subtype=None, parent_id=False, attachments=None, **kwargs):
        pass

    def message_subscribe(self, partner_ids, subtype_ids=None):
        pass
