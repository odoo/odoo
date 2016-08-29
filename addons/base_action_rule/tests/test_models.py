# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class LeadTest(models.Model):
    _name = "base.action.rule.lead.test"
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
    line_ids = fields.One2many('base.action.rule.line.test', 'lead_id')


class LineTest(models.Model):
    _name = "base.action.rule.line.test"
    _description = "Action Rule Line Test"

    name = fields.Char()
    lead_id = fields.Many2one('base.action.rule.lead.test', ondelete='cascade')
    user_id = fields.Many2one('res.users')
