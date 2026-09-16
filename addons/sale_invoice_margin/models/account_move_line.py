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


class AccountMoveLine(models.Model):
    """Inherited account move line for adding margin"""
    _inherit = 'account.move.line'

    margin_amount = fields.Float(string='Margin Amount', store=True,
                                 compute='_compute_margin',
                                 digits='Product Price',
                                 help='The total margin amount for the invoice')
    margin_percentage = fields.Float(string='Margin Percentage',
                                     compute='_compute_margin', store=True,
                                     digits='Product Price',
                                     help='The percentage of margin')

    @api.depends('quantity', 'price_unit', 'discount')
    def _compute_margin(self):
        """Method for computing margin"""
        for line in self:
            line.margin_amount = False
            line.margin_percentage = False
            if line.product_id:
                sale_price = line.price_unit * line.quantity
                discount = (sale_price * line.discount) / 100
                cost = line.product_id.standard_price * line.quantity
                margin_amount = (sale_price - discount) - cost
                if cost:
                    line.margin_amount = margin_amount
                    if sale_price != 0:
                        line.margin_percentage = margin_amount / sale_price
                else:
                    line.margin_amount = margin_amount
                    line.margin_percentage = 1
