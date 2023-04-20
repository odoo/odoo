# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import float_compare


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    timesheet_ids = fields.Many2many('account.analytic.line', compute='_compute_timesheet_ids', string='Timesheet activities associated to this sale')
    timesheet_count = fields.Float(string='Timesheet activities', compute='_compute_timesheet_ids', groups="hr_timesheet.group_hr_timesheet_user")

    # override domain
    project_id = fields.Many2one(domain="[('pricing_type', '!=', 'employee_rate'), ('analytic_account_id', '!=', False), ('company_id', '=', company_id)]")
    timesheet_encode_uom_id = fields.Many2one('uom.uom', related='company_id.timesheet_encode_uom_id')
    timesheet_total_duration = fields.Integer("Timesheet Total Duration", compute='_compute_timesheet_total_duration', help="Total recorded duration, expressed in the encoding UoM, and rounded to the unit")

    def _compute_timesheet_ids(self):
        timesheet_groups = self.env['account.analytic.line'].sudo().read_group(
            [('so_line', 'in', self.mapped('order_line').ids), ('project_id', '!=', False)],
            ['so_line', 'ids:array_agg(id)'],
            ['so_line'])
        timesheets_per_sol = {group['so_line'][0]: (group['ids'], group['so_line_count']) for group in timesheet_groups}

        for order in self:
            timesheet_ids = []
            timesheet_count = 0
            for sale_line_id in order.order_line.filtered('is_service').ids:
                list_timesheet_ids, count = timesheets_per_sol.get(sale_line_id, ([], 0))
                timesheet_ids.extend(list_timesheet_ids)
                timesheet_count += count

            order.update({
                'timesheet_ids': self.env['account.analytic.line'].browse(timesheet_ids),
                'timesheet_count': timesheet_count,
            })

    @api.depends('company_id.project_time_mode_id', 'timesheet_ids', 'company_id.timesheet_encode_uom_id')
    def _compute_timesheet_total_duration(self):
        if not self.user_has_groups('hr_timesheet.group_hr_timesheet_user'):
            self.update({'timesheet_total_duration': 0})
            return
        group_data = self.env['account.analytic.line'].sudo()._read_group([
            ('order_id', 'in', self.ids), ('project_id', '!=', False)
        ], ['order_id', 'unit_amount'], ['order_id'])
        timesheet_unit_amount_dict = defaultdict(float)
        timesheet_unit_amount_dict.update({data['order_id'][0]: data['unit_amount'] for data in group_data})
        for sale_order in self:
            total_time = sale_order.company_id.project_time_mode_id._compute_quantity(timesheet_unit_amount_dict[sale_order.id], sale_order.timesheet_encode_uom_id)
            sale_order.timesheet_total_duration = round(total_time)

    def _compute_field_value(self, field):
        if field.name != 'invoice_status' or self.env.context.get('mail_activity_automation_skip'):
            return super()._compute_field_value(field)

        # Get SOs which their state is not equal to upselling and if at least a SOL has warning prepaid service upsell set to True and the warning has not already been displayed
        upsellable_orders = self.filtered(lambda so:
            so.state == 'sale'
            and so.invoice_status != 'upselling'
            and so.id
            and (so.user_id or so.partner_id.user_id)  # salesperson needed to assign upsell activity
        )
        super(SaleOrder, upsellable_orders.with_context(mail_activity_automation_skip=True))._compute_field_value(field)
        for order in upsellable_orders:
            upsellable_lines = order._get_prepaid_service_lines_to_upsell()
            if upsellable_lines:
                order._create_upsell_activity()
                # We want to display only one time the warning for each SOL
                upsellable_lines.write({'has_displayed_warning_upsell': True})
        super(SaleOrder, self - upsellable_orders)._compute_field_value(field)

    def _get_prepaid_service_lines_to_upsell(self):
        """ Retrieve all sols which need to display an upsell activity warning in the SO

            These SOLs should contain a product which has:
                - type="service",
                - service_policy="ordered_prepaid",
        """
        self.ensure_one()
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        return self.order_line.filtered(lambda sol:
            sol.is_service
            and not sol.has_displayed_warning_upsell  # we don't want to display many times the warning each time we timesheet on the SOL
            and sol.product_id.service_policy == 'ordered_prepaid'
            and float_compare(
                sol.qty_delivered,
                sol.product_uom_qty * (sol.product_id.service_upsell_threshold or 1.0),
                precision_digits=precision
            ) > 0
        )

    def action_view_timesheet(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale_timesheet.timesheet_action_from_sales_order")
        action['context'] = {
            'search_default_billable_timesheet': True
        }  # erase default filters
        if self.order_line:
            tasks = self.order_line.task_id._filter_access_rules_python('write')
            if tasks:
                action['context']['default_task_id'] = tasks[0].id
            else:
                projects = self.order_line.project_id._filter_access_rules_python('write')
                if projects:
                    action['context']['default_project_id'] = projects[0].id
        if self.timesheet_count > 0:
            action['domain'] = [('so_line', 'in', self.order_line.ids), ('project_id', '!=', False)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def _create_invoices(self, grouped=False, final=False, date=None):
        """Link timesheets to the created invoices. Date interval is injected in the
        context in sale_make_invoice_advance_inv wizard.
        """
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        moves._link_timesheets_to_invoice(self.env.context.get("timesheet_start_date"), self.env.context.get("timesheet_end_date"))
        return moves


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    qty_delivered_method = fields.Selection(selection_add=[('timesheet', 'Timesheets')])
    analytic_line_ids = fields.One2many(domain=[('project_id', '=', False)])  # only analytic lines, not timesheets (since this field determine if SO line came from expense)
    remaining_hours_available = fields.Boolean(compute='_compute_remaining_hours_available', compute_sudo=True)
    remaining_hours = fields.Float('Remaining Hours on SO', compute='_compute_remaining_hours', compute_sudo=True, store=True)
    has_displayed_warning_upsell = fields.Boolean('Has Displayed Warning Upsell')
    timesheet_ids = fields.One2many('account.analytic.line', 'so_line', domain=[('project_id', '!=', False)], string='Timesheets')

    def name_get(self):
        res = super(SaleOrderLine, self).name_get()
        with_remaining_hours = self.env.context.get('with_remaining_hours')
        if with_remaining_hours:
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
                        remaining_time = ' ({sign}{hours:02.0f}:{minutes:02.0f})'.format(
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
            is_ordered_prepaid = line.product_id.service_policy == 'ordered_prepaid'
            is_time_product = line.product_uom.category_id == uom_hour.category_id
            line.remaining_hours_available = is_ordered_prepaid and is_time_product

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

    @api.depends('analytic_line_ids.project_id', 'project_id.pricing_type')
    def _compute_qty_delivered(self):
        super(SaleOrderLine, self)._compute_qty_delivered()

        lines_by_timesheet = self.filtered(lambda sol: sol.qty_delivered_method == 'timesheet')
        domain = lines_by_timesheet._timesheet_compute_delivered_quantity_domain()
        mapping = lines_by_timesheet.sudo()._get_delivered_quantity_by_analytic(domain)
        for line in lines_by_timesheet:
            line.qty_delivered = mapping.get(line.id or line._origin.id, 0.0)

    def _timesheet_compute_delivered_quantity_domain(self):
        """ Hook for validated timesheet in addionnal module """
        domain = [('project_id', '!=', False)]
        if self._context.get('accrual_entry_date'):
            domain += [('date', '<=', self._context['accrual_entry_date'])]
        return domain

    ###########################################
    # Service : Project and task generation
    ###########################################

    def _convert_qty_company_hours(self, dest_company):
        company_time_uom_id = dest_company.project_time_mode_id
        planned_hours = 0.0
        product_uom = self.product_uom
        if product_uom == self.env.ref('uom.product_uom_unit'):
            product_uom = self.env.ref('uom.product_uom_hour')
        if product_uom.category_id == company_time_uom_id.category_id:
            if product_uom != company_time_uom_id:
                planned_hours = product_uom._compute_quantity(self.product_uom_qty, company_time_uom_id)
            else:
                planned_hours = self.product_uom_qty
        return planned_hours

    def _timesheet_create_project(self):
        project = super()._timesheet_create_project()
        project_uom = project.timesheet_encode_uom_id
        timesheet_uom = self.company_id.timesheet_encode_uom_id
        uom_ids = set(project_uom + self.order_id.order_line.mapped('product_uom'))
        uom_unit = self.env.ref('uom.product_uom_unit')
        uom_hour = self.env.ref('uom.product_uom_hour')

        uom_per_id = {}
        for uom in uom_ids:
            if uom == uom_unit:
                uom = uom_hour
            if uom.category_id == project_uom.category_id:
                uom_per_id[uom.id] = uom

        allocated_hours = 0.0
        for line in self.order_id.order_line:
            product_type = line.product_id.service_tracking
            if line.is_service and (product_type == 'task_in_project' or product_type == 'project_only') and line.product_id.project_template_id == self.product_id.project_template_id:
                if uom_per_id.get(line.product_uom.id) or line.product_uom.id == uom_unit.id:
                    allocated_hours += line.product_uom_qty * uom_per_id.get(line.product_uom.id, project_uom).factor_inv * timesheet_uom.factor

        project.write({
            'allocated_hours': allocated_hours,
            'allow_timesheets': True,
        })
        return project

    def _timesheet_create_project_prepare_values(self):
        """Generate project values"""
        values = super()._timesheet_create_project_prepare_values()
        values['allow_billable'] = True
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
            qty_to_invoice = mapping.get(line.id, 0.0)
            if qty_to_invoice:
                line.qty_to_invoice = qty_to_invoice
            else:
                prev_inv_status = line.invoice_status
                line.qty_to_invoice = qty_to_invoice
                line.invoice_status = prev_inv_status

    def _get_action_per_item(self):
        """ Get action per Sales Order Item

            When the Sales Order Item contains a service product then the action will be View Timesheets.

            :returns: Dict containing id of SOL as key and the action as value
        """
        action_per_sol = super()._get_action_per_item()
        timesheet_action = self.env.ref('sale_timesheet.timesheet_action_from_sales_order_item').id
        timesheet_ids_per_sol = {}
        if self.user_has_groups('hr_timesheet.group_hr_timesheet_user'):
            timesheet_read_group = self.env['account.analytic.line']._read_group([('so_line', 'in', self.ids), ('project_id', '!=', False)], ['so_line', 'ids:array_agg(id)'], ['so_line'])
            timesheet_ids_per_sol = {res['so_line'][0]: res['ids'] for res in timesheet_read_group}
        for sol in self:
            timesheet_ids = timesheet_ids_per_sol.get(sol.id, [])
            if sol.is_service and len(timesheet_ids) > 0:
                action_per_sol[sol.id] = timesheet_action, timesheet_ids[0] if len(timesheet_ids) == 1 else False
        return action_per_sol
