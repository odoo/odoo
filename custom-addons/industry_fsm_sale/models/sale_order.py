# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import api, models, fields, _
from odoo.tools import float_is_zero

class SaleOrder(models.Model):
    _inherit = ['sale.order']

    task_id = fields.Many2one('project.task', string="Task", help="Task from which this quotation have been created")

    @api.model_create_multi
    def create(self, vals):
        orders = super().create(vals)
        for sale_order in orders:
            if sale_order.task_id:
                message = _("Extra Quotation Created: %s", sale_order._get_html_link())
                sale_order.task_id.message_post(body=message)
        return orders

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('fsm_no_message_post'):
            return False
        return super().message_post(**kwargs)

    def action_confirm(self):
        res = super().action_confirm()
        for sale_order in self:
            if sale_order.task_id:
                message = _("This Sales Order has been created from Task: %s", sale_order.task_id._get_html_link())
                sale_order.message_post(body=message)
        return res

    def _get_product_catalog_record_lines(self, product_ids):
        """
            Accessing the catalog from the smart button of a "field service" should compute
            the content of the catalog related to that field service rather than the content
            of the catalog related to the sale order containing that "field service".
        """
        task_id = self.env.context.get('fsm_task_id')
        if task_id:
            grouped_lines = defaultdict(lambda: self.env['sale.order.line'])
            for line in self.order_line:
                if line.task_id.id == task_id and line.product_id.id in product_ids:
                    grouped_lines[line.product_id] |= line
            return grouped_lines
        return super()._get_product_catalog_record_lines(product_ids)


class SaleOrderLine(models.Model):
    _inherit = ['sale.order.line']

    delivered_price_subtotal = fields.Monetary(compute='_compute_delivered_amount', string='Delivered Subtotal')
    delivered_price_tax = fields.Float(compute='_compute_delivered_amount', string='Delivered Total Tax')
    delivered_price_total = fields.Monetary(compute='_compute_delivered_amount', string='Delivered Total')

    @api.depends('qty_delivered', 'discount', 'price_unit', 'tax_id')
    def _compute_delivered_amount(self):
        """
        Compute the amounts of the SO line for delivered quantity.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.qty_delivered, product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.delivered_price_tax = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
            line.delivered_price_total = taxes['total_included']
            line.delivered_price_subtotal = taxes['total_excluded']

    def _timesheet_create_task_prepare_values(self, project):
        res = super(SaleOrderLine, self)._timesheet_create_task_prepare_values(project)
        if project.is_fsm:
            res.update({'partner_id': self.order_id.partner_shipping_id.id})
        return res

    def _timesheet_create_project_prepare_values(self):
        """Generate project values"""
        values = super(SaleOrderLine, self)._timesheet_create_project_prepare_values()
        if self.product_id.project_template_id.is_fsm:
            values.pop('sale_line_id', False)
        return values

    def _compute_invoice_status(self):
        sol_from_task_without_amount = self.filtered(
            lambda sol:
                sol.task_id.is_fsm
                and float_is_zero(sol.price_unit, precision_rounding=sol.currency_id.rounding)
        )
        sol_from_task_without_amount.invoice_status = 'no'
        super(SaleOrderLine, self - sol_from_task_without_amount)._compute_invoice_status()

    @api.depends('price_unit')
    def _compute_qty_to_invoice(self):
        sol_from_task_without_amount = self.filtered(
            lambda sol:
                sol.task_id.is_fsm
                and float_is_zero(sol.price_unit, precision_rounding=sol.currency_id.rounding)
        )
        sol_from_task_without_amount.qty_to_invoice = 0.0
        super(SaleOrderLine, self - sol_from_task_without_amount)._compute_qty_to_invoice()

    def action_add_from_catalog(self):
        if len(self.task_id) == 1 and self.task_id.allow_material:
            return self.task_id.action_fsm_view_material()
        return super().action_add_from_catalog()
