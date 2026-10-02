# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Ammu Raj (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
from odoo import api, fields, models


class AccountMove(models.Model):
    """Inherited account move for adding margin"""
    _inherit = "account.move"

    margin_amount = fields.Float(string='Margin Amount',
                                 compute='_compute_margin',
                                 digits='Product Price', store=True,
                                 help='The total margin amount for the invoice')
    margin_percentage = fields.Float(string='Margin Percentage',
                                     compute='_compute_margin', store=True,
                                     digits='Product Price',
                                     help='The percentage of margin')

    @api.depends('invoice_line_ids', 'invoice_line_ids.quantity',
                 'invoice_line_ids.price_unit', 'invoice_line_ids.discount')
    def _compute_margin(self):
        """Method for computing margin"""
        line_cost = lines_margin_amount = lines_sale_price = 0.0
        for move in self:
            move.margin_amount = False
            move.margin_percentage = False
            if move.invoice_line_ids:
                for line in move.invoice_line_ids:
                    sale_price = line.price_unit * line.quantity
                    lines_sale_price += sale_price
                    discount = (sale_price * line.discount) / 100
                    cost = line.product_id.standard_price * line.quantity
                    line_cost += cost
                    line_margin_amount = (sale_price - discount) - cost
                    lines_margin_amount += line_margin_amount
                if line_cost:
                    move.margin_amount = lines_margin_amount
                    if lines_sale_price != 0:
                        move.margin_percentage = \
                            lines_margin_amount / lines_sale_price
                else:
                    move.margin_amount = lines_margin_amount
                    move.margin_percentage = 1
