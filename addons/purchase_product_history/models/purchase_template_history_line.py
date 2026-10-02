# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Sruthi MK (odoo@cybrosys.com)
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
###############################################################################
from odoo import fields, models


class PurchaseTemplateHistoryLine(models.Model):
    """Purchase product history datas for product.template"""
    _name = 'purchase.template.history.line'
    _description = 'Purchase history line for template'

    history_id = fields.Many2one('product.template', string='Product',
                                 help='Name of the product variant')
    order_reference_id = fields.Many2one('purchase.order', string='Order',
                                         help='Purchase order reference of the'
                                              ' product')
    description = fields.Text(string='Description', help='Description of the'
                                                         ' product')
    price_unit = fields.Float(string='Unit Price', help='Unit price of the'
                                                        ' product')
    product_qty = fields.Float(string='Quantity', help='Product quantity')
    price_subtotal = fields.Float(string='Subtotal', help='Subtotal of the'
                                                          'product')
