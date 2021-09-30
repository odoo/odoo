# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.osv import expression
import math


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    timesheet_ids = fields.Many2many('account.analytic.line', compute='_compute_timesheet_ids', string='Timesheet activities associated to this sale')
    timesheet_count = fields.Float(string='Timesheet activities', compute='_compute_timesheet_ids', groups="hr_timesheet.group_hr_timesheet_user")

    # override domain
    project_id = fields.Many2one(domain="['|', ('bill_type', '=', 'customer_task'), ('pricing_type', '=', 'fixed_rate'), ('analytic_account_id', '!=', False), ('company_id', '=', company_id)]")
    timesheet_encode_uom_id = fields.Many2one('uom.uom', related='company_id.timesheet_encode_uom_id')
    timesheet_total_duration = fields.Integer("Timesheet Total Duration", compute='_compute_timesheet_total_duration', help="Total recorded duration, expressed in the encoding UoM, and rounded to the unit")

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
            total_time = 0.0
            for timesheet in timesheets.filtered(lambda t: not t.non_allow_billable):
                # Timesheets may be stored in a different unit of measure, so first we convert all of them to the reference unit
                total_time += timesheet.unit_amount * timesheet.product_uom_id.factor_inv
            # Now convert to the proper unit of measure
            total_time *= sale_order.timesheet_encode_uom_id.factor
            sale_order.timesheet_total_duration = total_time

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
        action = self.env["ir.actions.actions"]._for_xml_id("sale_timesheet.timesheet_action_from_sales_order")
        action['context'] = {
            'search_default_billable_timesheet': True
        }  # erase default filters
        if self.timesheet_count > 0:
            action['domain'] = [('so_line', 'in', self.order_line.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def _create_invoices(self, grouped=False, final=False, start_date=None, end_date=None):
        """ Override the _create_invoice method in sale.order model in sale module
            Add new parameter in this method, to invoice sale.order with a date. This date is used in sale_make_invoice_advance_inv into this module.
            :param start_date: the start date of the period
            :param end_date: the end date of the period
            :return {account.move}: the invoices created
        """
        moves = super(SaleOrder, self)._create_invoices(grouped, final)
        moves._link_timesheets_to_invoice(start_date, end_date)
        return moves

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    qty_delivered_method = fields.Selection(selection_add=[('timesheet', 'Timesheets')])
    analytic_line_ids = fields.One2many(domain=[('project_id', '=', False)])  # only analytic lines, not timesheets (since this field determine if SO line came from expense)
    remaining_hours_available = fields.Boolean(compute='_compute_remaining_hours_available')
    remaining_hours = fields.Float('Remaining Hours on SO', compute='_compute_remaining_hours')

    def name_get(self):
        res = super(SaleOrderLine, self).name_get()
        if self.env.context.get('with_remaining_hours'):
            names = dict(res)
            result = []
            uom_hour = self.env.ref('uom.product_uom_hour')
            uom_day = self.env.ref('uom.product_uom_day')
            for line in self:
                name = names.get(line.id)
                if line.remaining_hours_available:
                    company = self.env.company
                    encoding_uom = company.timesheet_encode_uom_id
                    remaining_time = ''
                    if encoding_uom == uom_hour:
                        hours, minutes = divmod(abs(line.remaining_hours) * 60, 60)
                        round_minutes = minutes / 30
                        minutes = math.ceil(round_minutes) if line.remaining_hours >= 0 else math.floor(round_minutes)
                        if minutes > 1:
                            minutes = 0
                            hours += 1
                        else:
                            minutes = minutes * 30
                        remaining_time =' ({sign}{hours:02.0f}:{minutes:02.0f})'.format(
                            sign='-' if line.remaining_hours < 0 else '',
                            hours=hours,
                            minutes=minutes)
                    elif encoding_uom == uom_day:
                        remaining_days = company.project_time_mode_id._compute_quantity(line.remaining_hours, encoding_uom, round=False)
                        remaining_time = ' ({qty:.02f} {unit})'.format(
                            qty=remaining_days,
                            unit=_('days') if abs(remaining_days) > 1 else _('day')
                        )
                    name = '{name}{remaining_time}'.format(
                        name=name,
                        remaining_time=remaining_time
                    )
                result.append((line.id, name))
            return result
        return res

    @api.depends('product_id.service_policy')
    def _compute_remaining_hours_available(self):
        uom_hour = self.env.ref('uom.product_uom_hour')
        for line in self:
            is_ordered_timesheet = line.product_id.service_policy == 'ordered_timesheet'
            is_time_product = line.product_uom.category_id == uom_hour.category_id
            line.remaining_hours_available = is_ordered_timesheet and is_time_product

    @api.depends('qty_delivered', 'product_uom_qty', 'analytic_line_ids')
    def _compute_remaining_hours(self):
        uom_hour = self.env.ref('uom.product_uom_hour')
        for line in self:
            remaining_hours = None
            if line.remaining_hours_available:
                qty_left = line.product_uom_qty - line.qty_delivered
                remaining_hours = line.product_uom._compute_quantity(qty_left, uom_hour)
            line.remaining_hours = remaining_hours

    @api.depends('product_id')
    def _compute_qty_delivered_method(self):
        """ Sale Timesheet module compute delivered qty for product [('type', 'in', ['service']), ('service_type', '=', 'timesheet')] """
        super(SaleOrderLine, self)._compute_qty_delivered_method()
        for line in self:
            if not line.is_expense and line.product_id.type == 'service' and line.product_id.service_type == 'timesheet':
                line.qty_delivered_method = 'timesheet'

    @api.depends('analytic_line_ids.project_id', 'analytic_line_ids.non_allow_billable', 'project_id.pricing_type', 'project_id.bill_type')
    def _compute_qty_delivered(self):
        super(SaleOrderLine, self)._compute_qty_delivered()

        lines_by_timesheet = self.filtered(lambda sol: sol.qty_delivered_method == 'timesheet')
        domain = lines_by_timesheet._timesheet_compute_delivered_quantity_domain()
        mapping = lines_by_timesheet.sudo()._get_delivered_quantity_by_analytic(domain)
        for line in lines_by_timesheet:
            line.qty_delivered = mapping.get(line.id or line._origin.id, 0.0)

    def _timesheet_compute_delivered_quantity_domain(self):
        """ Hook for validated timesheet in addionnal module """
        return [('project_id', '!=', False), ('non_allow_billable', '=', False)]

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

    def _timesheet_create_project_prepare_values(self):
        """Generate project values"""
        values = super()._timesheet_create_project_prepare_values()
        values['allow_billable'] = True
        values['bill_type'] = 'customer_project'
        values['pricing_type'] = 'fixed_rate'
        return values

    def _recompute_qty_to_invoice(self, start_date, end_date):
        """ Recompute the qty_to_invoice field for product containing timesheets

            Search the existed timesheets between the given period in parameter.
            Retrieve the unit_amount of this timesheet and then recompute
            the qty_to_invoice for each current product.

            :param start_date: the start date of the period
            :param end_date: the end date of the period
        """
        lines_by_timesheet = self.filtered(lambda sol: sol.product_id and sol.product_id._is_delivered_timesheet())
        domain = lines_by_timesheet._timesheet_compute_delivered_quantity_domain()
        refund_account_moves = self.order_id.invoice_ids.filtered(lambda am: am.state == 'posted' and am.move_type == 'out_refund').reversed_entry_id
        timesheet_domain = [
            '|',
            ('timesheet_invoice_id', '=', False),
            ('timesheet_invoice_id.state', '=', 'cancel')]
        if refund_account_moves:
            credited_timesheet_domain = [('timesheet_invoice_id.state', '=', 'posted'), ('timesheet_invoice_id', 'in', refund_account_moves.ids)]
            timesheet_domain = expression.OR([timesheet_domain, credited_timesheet_domain])
        domain = expression.AND([domain, timesheet_domain])
        if start_date:
            domain = expression.AND([domain, [('date', '>=', start_date)]])
        if end_date:
            domain = expression.AND([domain, [('date', '<=', end_date)]])
        mapping = lines_by_timesheet.sudo()._get_delivered_quantity_by_analytic(domain)

        for line in lines_by_timesheet:
            line.qty_to_invoice = mapping.get(line.id, 0.0)
