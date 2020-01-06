# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    timesheet_ids = fields.Many2many('account.analytic.line', compute='_compute_timesheet_ids', string='Timesheet activities associated to this sale')
    timesheet_count = fields.Float(string='Timesheet activities', compute='_compute_timesheet_ids', groups="hr_timesheet.group_hr_timesheet_user")

    # override domain
    project_id = fields.Many2one(domain="[('billable_type', 'in', ('no', 'task_rate')), ('analytic_account_id', '!=', False), ('company_id', '=', company_id)]")
    timesheet_encode_uom_id = fields.Many2one('uom.uom', related='company_id.timesheet_encode_uom_id')
    timesheet_total_duration = fields.Float("Timesheet Total Duration", compute='_compute_timesheet_total_duration', help="Total recorded duration, expressed in the encoding UoM")

    @api.depends('analytic_account_id.line_ids')
    def _compute_timesheet_ids(self):
        for order in self:
            if order.analytic_account_id:
                order.timesheet_ids = self.env['account.analytic.line'].search(
                    [('so_line', 'in', order.order_line.ids),
                        ('amount', '<=', 0.0),
                        ('project_id', '!=', False)])
            else:
                order.timesheet_ids = []
            order.timesheet_count = len(order.timesheet_ids)

    @api.depends('timesheet_ids', 'company_id.timesheet_encode_uom_id')
    def _compute_timesheet_total_duration(self):
        for sale_order in self:
            timesheets = sale_order.timesheet_ids if self.user_has_groups('hr_timesheet.group_hr_timesheet_approver') else sale_order.timesheet_ids.filtered(lambda t: t.user_id.id == self.env.uid)
            sale_order.timesheet_total_duration = sum([timesheet.unit_amount for timesheet in timesheets])

    def action_view_project_ids(self):
        self.ensure_one()
        # redirect to form or kanban view
        billable_projects = self.project_ids.filtered(lambda project: project.sale_line_id)
        if len(billable_projects) == 1 and self.env.user.has_group('project.group_project_manager'):
            action = billable_projects[0].action_view_timesheet_plan()
        else:
            action = super().action_view_project_ids()
        return action

    def action_view_timesheet(self):
        self.ensure_one()
        action = self.env.ref('sale_timesheet.timesheet_action_from_sales_order').read()[0]
        ctx = dict(self.env.context or {})
        ctx.pop('group_by', None)
        action['context'] = ctx  # erase default filters
        if self.timesheet_count > 0:
            action['domain'] = [('so_line', 'in', self.order_line.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def _create_invoices(self, grouped=False, final=False, date=None):
        """ Override the _create_invoice method in sale.order model in sale module
            Add new parameter in this method, to invoice sale.order with a date. This date is used in sale_make_invoice_advance_inv into this module.
            :param date
            :return {account.move}: the invoices created
        """
        moves = super(SaleOrder, self)._create_invoices(grouped, final)
        moves._link_timesheets_to_invoice(date)
        return moves

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    qty_delivered_method = fields.Selection(selection_add=[('timesheet', 'Timesheets')])
    analytic_line_ids = fields.One2many(domain=[('project_id', '=', False)])  # only analytic lines, not timesheets (since this field determine if SO line came from expense)

    @api.depends('product_id')
    def _compute_qty_delivered_method(self):
        """ Sale Timesheet module compute delivered qty for product [('type', 'in', ['service']), ('service_type', '=', 'timesheet')] """
        super(SaleOrderLine, self)._compute_qty_delivered_method()
        for line in self:
            if not line.is_expense and line.product_id.type == 'service' and line.product_id.service_type == 'timesheet':
                line.qty_delivered_method = 'timesheet'

    @api.depends('analytic_line_ids.project_id')
    def _compute_qty_delivered(self):
        super(SaleOrderLine, self)._compute_qty_delivered()

        lines_by_timesheet = self.filtered(lambda sol: sol.qty_delivered_method == 'timesheet')
        domain = lines_by_timesheet._timesheet_compute_delivered_quantity_domain()
        mapping = lines_by_timesheet.sudo()._get_delivered_quantity_by_analytic(domain)
        for line in lines_by_timesheet:
            line.qty_delivered = mapping.get(line.id or line._origin.id, 0.0)

    def _timesheet_compute_delivered_quantity_domain(self):
        """ Hook for validated timesheet in addionnal module """
        return [('project_id', '!=', False)]

    ###########################################
    # Service : Project and task generation
    ###########################################

    def _convert_qty_company_hours(self, dest_company):
        company_time_uom_id = dest_company.project_time_mode_id
        if self.product_uom.id != company_time_uom_id.id and self.product_uom.category_id.id == company_time_uom_id.category_id.id:
            planned_hours = self.product_uom._compute_quantity(self.product_uom_qty, company_time_uom_id)
        else:
            planned_hours = self.product_uom_qty
        return planned_hours

    def _timesheet_create_project(self):
        project = super()._timesheet_create_project()
        project.write({'allow_timesheets': True})
        return project

    def _recompute_qty_to_invoice(self, date):
        """ Recompute the qty_to_invoice field for product containing timesheets

            Search the existed timesheets up the given date in parameter.
            Retrieve the unit_amount of this timesheet and then recompute
            the qty_to_invoice for each current product.

            :param date: date to search timesheets before this date.
        """
        lines_by_timesheet = self.filtered(lambda sol: sol.product_id._is_delivered_timesheet())
        domain = lines_by_timesheet._timesheet_compute_delivered_quantity_domain()
        domain = expression.AND([domain, [
            ('date', '<=', date),
            ('timesheet_invoice_id', '=', False)]])
        mapping = lines_by_timesheet.sudo()._get_delivered_quantity_by_analytic(domain)

        for line in lines_by_timesheet:
            if line.product_id._is_delivered_timesheet():
                line.qty_to_invoice = mapping.get(line.id, 0.0)
