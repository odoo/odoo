# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models


class SaleOrderLine(models.Model):
    """This class is for displaying margin on  SaleOrderLine"""
    _inherit = 'sale.order.line'

    cost_price_sale = fields.Float(string='Cost',
                                   compute='compute_cost_price',
                                   store=True, help='Field for cost price')
    margin_amount_sale = fields.Float(string='Margin Amount',
                                      compute='compute_margin_amount',
                                      store=True,
                                      help='Field for margin amount')

    @api.depends('product_id')
    def compute_cost_price(self):
        """ Compute the cost price of the line. """
        self.cost_price_sale = 0
        for record in self:
            if record.product_id:
                record.cost_price_sale = record.product_id.standard_price

    @api.depends('product_id')
    def compute_margin_amount(self):
        """ Compute the margin amount of the line. """
        self.margin_amount_sale = 0
        for record in self:
            if record.price_unit and record.cost_price_sale:
                record.margin_amount_sale = record.price_unit - record.cost_price_sale


class SaleOrder(models.Model):
    """This class is used to display margin on sale order."""
    _inherit = 'sale.order'

    margin_percent_sale = fields.Float(string='Margin %',
                                       help='Field for margin in percentage')
    margin_amount_sale_total = fields.Float(string='Margin Amount',
                                            help='Field for Margin amount in total ')

    def action_confirm(self):
        """Method for confirm sale order and set values to margin and margin
        percent"""
        res = super(SaleOrder, self).action_confirm()
        for record in self:
            if record.order_line.product_id:
                record.margin_amount_sale_total = sum(
                    record.order_line.mapped('margin_amount_sale'))
                record.margin_percent_sale = record.margin_amount_sale_total / record.amount_total
        return res
