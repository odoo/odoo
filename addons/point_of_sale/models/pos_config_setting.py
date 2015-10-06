# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models


class PosConfiguration(models.TransientModel):
    _inherit = 'base.config.settings'
    _name = 'pos.config.settings'

    module_pos_restaurant = fields.Selection([
        (0, "Point of sale for shops"),
        (1, "Restaurant: activate table management")
    ], "Restaurant",
        help='This module adds several restaurant features to the Point of Sale: \n\n- Bill Printing: Allows you to print a receipt before the order is paid \n\n- Bill Splitting: Allows you to split an order into different orders \n\n- Kitchen Order Printing: allows you to print orders updates to kitchen or bar printers')
    module_pos_loyalty = fields.Selection([
        (0, "No loyalty programs"),
        (1, "Use loyalty programs")
    ], "Loyalty",
        help='Allows you to define a loyalty program in the point of sale, where the customers earn loyalty points and get rewards')
    module_pos_discount = fields.Selection([
        (0, "Allow discounts on order lines only"),
        (1, "Allow global discounts")
    ], "Discount",
        help='Allows the cashier to quickly give a percentage sale discount for all the sales order to a customer')
    module_pos_mercury = fields.Selection([
        (0, "No credit card"),
        (1, "Allows customers to pay with credit cards.")
    ], "Credit Cards",
        help='The transactions are processed by MercuryPay')
    module_pos_reprint = fields.Selection([
        (0, "No reprint"),
        (1, "Allow cashier to reprint receipts")
    ], "Reprints")
