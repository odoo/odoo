# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Jumana Jabin MP (<https://www.cybrosys.com>)
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
from odoo import fields, models


class ProductInvoiceHistory(models.TransientModel):
    """Product Invoice History model for storing invoice line details."""
    _name = 'product.invoice.history'
    _description = 'Product Invoice History'

    product_details_id = fields.Many2one('invoice.product.details',
                                         string='Product Details',
                                         help='The associated product'
                                              ' details for the invoice')
    date = fields.Datetime(string='Date', help='The date of the invoice')
    move_id = fields.Many2one('account.move', string='Invoice/Bill',
                              help='The associated account move for the '
                                   'invoice')
    account_move_number = fields.Char(string='Invoice/Bill No',
                                      help='The number of the invoice/bill')
    partner_id = fields.Many2one('res.partner', string='Customer/Vendor',
                                 help='The customer or vendor associated '
                                      'with the invoice')
    price_unit = fields.Float(string='Unit Price',
                              help='The unit price of the product or service')
    total = fields.Float(string='Total',
                         help='The total amount for the invoice')
    qty = fields.Float(string='Quantity',
                       help='The quantity of the product or service')
    type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bill')
    ], string='Type',
        help='The type of the invoice (customer invoice or vendor bill)')
