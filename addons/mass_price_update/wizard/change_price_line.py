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


class ChangePriceLine(models.TransientModel):
    """One2many for align the products with new price"""
    _name = 'change.price.line'
    _rec_name = 'product_id'
    _description = "Change Price Line"

    mass_price_update_id = fields.Many2one('mass.price.update', string='Number',
                                           help='The related field from mass'
                                                'price update')
    product_id = fields.Many2one(
        'product.product', string='Product', required=True,
        domain="[('active', '=', True)]", help='Selected products will show')
    current_price = fields.Float(string='Current Price', digits='Product Price',
                                 related='product_id.lst_price',
                                 help='The current Sales price')
    new_price = fields.Float(string='New Price', digits='Product Price',
                             compute='_compute_new_price_cost',
                             help='Computing the new price based on the percentage')
    current_cost = fields.Float(string='Current Cost', digits='Product Price',
                                related='product_id.standard_price',
                                help='Current cost of the product')
    new_cost = fields.Float(string='New Cost', digits='Product Price',
                            compute='_compute_new_price_cost',
                            help='Computing the new cost based on the'
                                 'percentage')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related='product_id.currency_id',
                                  help='The currency of the product')

    @api.depends('mass_price_update_id.apply_on',
                 'mass_price_update_id.change',
                 'mass_price_update_id.apply_type')
    def _compute_new_price_cost(self):
        """Compute new price and new cost"""
        for record in self:
            if record.mass_price_update_id.apply_type == 'add':
                percentage_num = 1 + record.mass_price_update_id.change
            else:
                percentage_num = 1 - record.mass_price_update_id.change
            if record.mass_price_update_id.apply_on == 'price':
                record.new_cost = False
                record.new_price = record.current_price * percentage_num
            else:
                record.new_price = False
                record.new_cost = record.current_cost * percentage_num
