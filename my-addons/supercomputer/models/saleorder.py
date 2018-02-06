# -*- coding: utf-8 -*-

from odoo import models, fields, api


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

    @api.depends('margin_per_product')
    def _compute_margin(self):
        for record in self:
            qty = record.product_uom_qty
            record.margin = qty * record.margin_per_product

    @api.onchange('price_unit')
    def _check_margin(self):
        print("function: onchange checkmargin", self.price_unit)
        print("margin_rate: ", self.margin_rate, self._compute_margin())
        if self.product_id.categ_id.minimum_margin < self.margin_rate:
            return {
                'warning': {
                    'title': "Margin below expectation!",
                    'message': "The current margin is below the expected minimum",
                },
            }

    @api.model
    def create(self, values):
        # print(self)
        min = self.env['product_id'].browse(values.product_id).categ_id.minimum_margin

        print("function: create", values['product_id'].categ_id.minimum_margin)

        # print(values)
        # {'sequence': 10, 'product_id': 23, 'layout_category_id': False, 'name': '[LAPTOP C2] Laptop Class 2', 'product_uom_qty': 1, 'product_uom': 1, 'analytic_tag_ids': [[6, False, []]], 'route_id': False, 'price_unit': 1000, 'tax_id': [[6, False, [2]]], 'discount': 0, 'customer_lead': 0, 'order_id': 10}

        if self.margin_rate < min:  # and not a sales manager
            return {
                'warning': {
                    'title': "Margin below expectation!",
                    'message': "You cannot sell under the minimum margin unless you are a manager.",
                },
            }
        else:
            res_id = super(SaleOrderLine, self).create(values)

        return res_id

    @api.model
    def write(self, values):
        min = self.env['product_id'].browse(values.product_id).categ_id.minimum_margin

        print("function: write", self.margin_rate, min)

        if self.margin_rate < min:  # and not a sales manager
            return {
                'warning': {
                    'title': "Margin below expectation!",
                    'message': "You cannot sell under the minimum margin unless you are a manager.",
                },
            }
        else:
            res_id = super(SaleOrderLine, self).create(values)

        return res_id

    """
    def write(self, vals):
        print 'Fields and the values to be updated/written--', vals
        # Write your logic here
        res = super(res_users, self).write(vals)
        # Write your logic here
        return res"""
