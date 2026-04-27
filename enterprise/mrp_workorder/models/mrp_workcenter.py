# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from odoo import models, fields, api
from odoo.http import request


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    employee_ids = fields.Many2many(
        'hr.employee', string="employees with access",
        help='if left empty, all employees can log in to the workcenter', store=True,
        readonly=False)
    currency_id = fields.Many2one(related='company_id.currency_id')
    employee_costs_hour = fields.Monetary(string='Employee Hourly Cost', currency_field='currency_id', default=0.0)

    def action_work_order(self):
        if self.env.user.has_group('mrp_workorder.group_mrp_wo_shop_floor') and not self.env.context.get('desktop_list_view', False):
            action = self.env["ir.actions.actions"]._for_xml_id("mrp_workorder.action_mrp_display")
        else:
            action = super().action_work_order()
        context = action.get('context', '{}')
        if 'active_id' not in context:
            context = context[:-1] + ",'workcenter_id':active_id}"
        if 'search_default_ready' in self.env.context:
            context = context[:-1] + ",'show_ready_workorders':1}"
        if 'search_default_progress' in self.env.context:
            context = context[:-1] + ",'show_progress_workorders':1}"
        context = context.replace('active_id', str(self.id))
        action['context'] = dict(literal_eval(context), employee_id=request.session.get('employee_id'), shouldHideNewWorkcenterButton=True)
        return action

    @api.model
    def get_employee_barcode(self, barcode):
        return self.env['hr.employee'].search([("barcode", "=", barcode)], limit=1).id

    @api.depends('time_ids', 'time_ids.date_end', 'time_ids.loss_type')
    def _compute_working_state(self):
        self.working_state = 'normal'
        time_log = self.env['mrp.workcenter.productivity'].search([
            ('workcenter_id', 'in', self.ids),
            ('date_end', '=', False),
        ])
        for time in time_log:
            if time.loss_type in ('productive', 'performance'):
                # the productivity line has a `loss_type` that means the workcenter is being used
                time.workcenter_id.working_state = 'done'
            else:
                # the workcenter is blocked
                time.workcenter_id.working_state = 'blocked'


class MrpWorkcenterProductivity(models.Model):
    _inherit = "mrp.workcenter.productivity"

    employee_id = fields.Many2one(
        'hr.employee', string="Employee", compute='_compute_employee',
        help='employee that record this working time', store=True, readonly=False)
    employee_cost = fields.Monetary('employee_cost', compute='_compute_employee_cost', default=0, store=True)
    total_cost = fields.Float('Cost', compute='_compute_total_cost')
    currency_id = fields.Many2one(related='company_id.currency_id')

    @api.depends('employee_id.hourly_cost')
    def _compute_employee_cost(self):
        for time in self:
            time.employee_cost = time.employee_id.hourly_cost if time.employee_id else time.workcenter_id.employee_costs_hour

    @api.depends('duration', 'employee_cost')
    def _compute_total_cost(self):
        for time in self:
            time.total_cost = time.employee_cost * time.duration / 60

    @api.depends('user_id')
    def _compute_employee(self):
        for time in self:
            if time.user_id and time.user_id.employee_id:
                time.employee_id = time.user_id.employee_id

    def _check_open_time_ids(self):
        # TODO make check on employees
        pass
