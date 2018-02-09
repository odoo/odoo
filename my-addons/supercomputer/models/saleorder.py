# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sum_commission = fields.Float(compute='_compute_sum_commission', store=True)

    @api.depends('order_line.product_id', 'order_line.price_unit', 'order_line.product_uom_qty')
    def _compute_sum_commission(self):
        for record in self:
            s = 0
            for line in record.order_line:
                pid = line.product_id
                com = pid.categ_id.rate * line.price_unit
                qty = line.product_uom_qty
                s += qty * com / 100
            record.sum_commission = s


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    margin_rate = fields.Float(compute='_compute_margin_rate', store=True)
    margin = fields.Float(compute='_compute_margin', store=True)
    margin_per_product = fields.Float(compute='_compute_margin_pp', store=True)

    @api.depends('product_id', 'price_unit')
    def _compute_margin_pp(self):
        for record in self:
            pid = record.product_id
            s = record.price_unit
            record.margin_per_product = s - (pid.standard_price + pid.categ_id.rate * s / 100)

    @api.depends('margin_per_product')
    def _compute_margin_rate(self):
        for record in self:
            print("function: compute", "Price_unit:", record.price_unit)
            if record.price_unit != 0:
                record.margin_rate = record.margin_per_product / record.price_unit * 100
                print("inside:", record.margin_per_product / record.price_unit * 100)
            else:
                record.margin_rate = 0

    @api.depends('margin_per_product', 'product_uom_qty')
    def _compute_margin(self):
        for record in self:
            qty = record.product_uom_qty
            record.margin = qty * record.margin_per_product

    @api.onchange('price_unit', 'margin_rate')
    def _check_margin(self):
        print("function: onchange checkmargin", self.price_unit)
        print("margin_rate: ", self.margin_rate, self._compute_margin())
        if self.margin_rate < self.product_id.categ_id.minimum_margin:
            return {
                'warning': {
                    'title': "Margin below expectation!",
                    'message': "The current margin is below the expected minimum",
                },
            }

    def create(self, values):
        res_id = super(SaleOrderLine, self).create(values)

        if res_id.margin_rate < res_id.product_id.categ_id.minimum_margin and \
                not res_id.env.user.has_group('sales_team.group_sale_manager'):
            raise UserError("Only a sales manager can sell below the minimum margin!")

        return res_id

    def write(self, values):
        for record in self:
            super(SaleOrderLine, record).write(values)

            if record.margin_rate < record.product_id.categ_id.minimum_margin and \
                    not record.env.user.has_group('sales_team.group_sale_manager'):
                raise UserError("Only a sales manager can sell below the minimum margin!")
        return True
