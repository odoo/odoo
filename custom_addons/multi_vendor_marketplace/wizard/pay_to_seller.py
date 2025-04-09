# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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
from odoo import fields, models


class PayToSeller(models.TransientModel):
    """Model to manage the payment of Sellers"""
    _name = 'pay.to.seller'

    date = fields.Date(string='Date', required=True, help='Date',
                       default=fields.Date.today())
    seller_id = fields.Many2one('res.partner', help='Sellers',
                                string='Seller', required=True)
    cashable_amount = fields.Float(string='Cashable Amount', default=0,
                                   help='Cashable Amount',
                                   related='seller_id.total_commission')
    payment_amount = fields.Float(string='Payment Amount', help='Payment '
                                                                'amount')
    payment_methode_id = fields.Selection([('cash', 'cash'),
                                           ('bank', 'bank')], help='Payment '
                                                                   'methods')
    payment_methods_id = fields.Many2one('account.payment.method.line',
                                         string='Payment Method',
                                         help='Payment Method')
    memo = fields.Char(string='Memo', required=True, help='Memo')
    payment_description = fields.Text(string='Payment Description',
                                      help='Payment Description',
                                      required=True)
