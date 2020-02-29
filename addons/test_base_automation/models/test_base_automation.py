# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil import relativedelta
from odoo import fields, models, api


class LeadTest(models.Model):
    _name = "base.automation.lead.test"
    _description = "Automated Rule Test"

    name = fields.Char(string='Subject', required=True, index=True)
    user_id = fields.Many2one('res.users', string='Responsible')
    state = fields.Selection([('draft', 'New'), ('cancel', 'Cancelled'), ('open', 'In Progress'),
                              ('pending', 'Pending'), ('done', 'Closed')],
                             string="Status", readonly=True, default='draft')
    active = fields.Boolean(default=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    date_action_last = fields.Datetime(string='Last Action', readonly=True)
    employee = fields.Boolean(compute='_compute_employee_deadline', store=True)
    line_ids = fields.One2many('base.automation.line.test', 'lead_id')

    priority = fields.Boolean()
    deadline = fields.Boolean(compute='_compute_employee_deadline', store=True)
    is_assigned_to_admin = fields.Boolean(string='Assigned to admin user')

    @api.depends('partner_id.employee', 'priority')
    def _compute_employee_deadline(self):
        # this method computes two fields on purpose; don't split it
        for record in self:
            record.employee = record.partner_id.employee
            if not record.priority:
                record.deadline = False
            else:
                record.deadline = record.create_date + relativedelta.relativedelta(days=3)

    def write(self, vals):
        result = super().write(vals)
        # force recomputation of field 'deadline' via 'employee': the action
        # based on 'deadline' must be triggered
        self.mapped('employee')
        return result


class LineTest(models.Model):
    _name = "base.automation.line.test"
    _description = "Automated Rule Line Test"

    name = fields.Char()
    lead_id = fields.Many2one('base.automation.lead.test', ondelete='cascade')
    user_id = fields.Many2one('res.users')


class ModelWithAccess(models.Model):
    _name = "base.automation.link.test"
    _description = "Automated Rule Link Test"

    name = fields.Char()
    linked_id = fields.Many2one('base.automation.linked.test', ondelete='cascade')


class ModelWithoutAccess(models.Model):
    _name = "base.automation.linked.test"
    _description = "Automated Rule Linked Test"

    name = fields.Char()
    another_field = fields.Char()
