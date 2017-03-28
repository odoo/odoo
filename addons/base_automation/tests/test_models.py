# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil import relativedelta
from odoo import fields, models, api


class LeadTest(models.Model):
    _name = "base.automation.lead.test"
    _description = "Action Rule Test"

    name = fields.Char(string='Subject', required=True, index=True)
    user_id = fields.Many2one('res.users', string='Responsible')
    state = fields.Selection([('draft', 'New'), ('cancel', 'Cancelled'), ('open', 'In Progress'),
                              ('pending', 'Pending'), ('done', 'Closed')],
                             string="Status", readonly=True, default='draft')
    active = fields.Boolean(default=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    date_action_last = fields.Datetime(string='Last Action', readonly=True)
    customer = fields.Boolean(related='partner_id.customer', readonly=True, store=True)
    line_ids = fields.One2many('base.automation.line.test', 'lead_id')

    priority = fields.Boolean()
    deadline = fields.Boolean(compute='_compute_deadline', store=True)
    is_assigned_to_admin = fields.Boolean(string='Assigned to admin user')

    @api.depends('priority')
    def _compute_deadline(self):
        for record in self:
            if not record.priority:
                record.deadline = False
            else:
                record.deadline = fields.Datetime.from_string(record.create_date) + relativedelta.relativedelta(days=3)

class LineTest(models.Model):
    _name = "base.automation.line.test"
    _description = "Action Rule Line Test"

    name = fields.Char()
    lead_id = fields.Many2one('base.automation.lead.test', ondelete='cascade')
    user_id = fields.Many2one('res.users')
