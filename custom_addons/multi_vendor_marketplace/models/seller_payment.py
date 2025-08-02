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
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.http import request


class SellerPayment(models.Model):
    """ Managing seller payments"""
    _name = 'seller.payment'
    _description = "Seller Payment"

    name = fields.Char(string='Record Reference', required=True,
                       help="Sequence of the payment", readonly=True,
                       default='New')
    seller_id = fields.Many2one(
        'res.partner', string='Seller',
        required=True,
        default=lambda self: self.env.user.partner_id.id,
        help="Seller details")
    payment_mode = fields.Selection(
        selection=[('Cash', 'Cash'),
                   ('Bank', 'Bank')],
        string="Payment Mode",
        help="To select the mode of payment",
        required=True, default='Cash')
    memo = fields.Char(string='Memo', help="Description", required=True)
    payable_amount = fields.Float(string='Payable Amount', help="Total amount",
                                  required=True)
    date = fields.Date(string='Payment Date', required=True,
                       help="Date of the payment", default=fields.Date.today)
    type_id = fields.Many2one('account.payment.method',
                              string='Type', help="Payment method",
                              required=True)
    invoice_cashable = fields.Boolean(string='Invoice Cashable',
                                      help="Total amount that to invoice")
    description = fields.Text(string='Description', help="Description")
    commission = fields.Float(string="Commission",
                              help="Total commission amount")
    state = fields.Selection(selection=[('Draft', 'Draft'),
                                        ('Requested', 'Requested'),
                                        ('Validated', 'Validated'),
                                        ('Rejected', 'Rejected'),
                                        ('cancelled', 'Cancelled')],
                             string="state",
                             help="State of the seller payment",
                             default="Draft")

    def request(self):
        """ Request for payment and check payment term settings values  """
        self.state = 'Requested'
        amount_limit = self.env['ir.config_parameter'].sudo().get_param(
            'multi_vendor_marketplace.amt_limit')
        min_gap = self.env['ir.config_parameter'].sudo().get_param(
            'multi_vendor_marketplace.min_gap')
        partner_id = self.env['res.partner'].search(
            [('id', '=', self.seller_id.id)])
        today_date = fields.Date.today()
        mingap_date = fields.Date.subtract(today_date, days=int(min_gap))
        date_info_record = self.env['seller.payment'].search(
            [('seller_id', '=', self.seller_id.id),
             ('state', '=', 'Validated'), ('date', '>=', mingap_date)],
            order='date DESC')
        for checkdate in date_info_record:
            if (self.payable_amount > partner_id.total_commission
                    or self.payable_amount > int(
                    amount_limit) or checkdate.date >= mingap_date):
                raise ValidationError(
                    _("Entered amount is greater than your commission or "
                      "Amount limit is " + amount_limit + " and Minimum gap "
                        "for next payment request " + min_gap + " days"))
            break

    def reject(self):
        """ Payment request will reject """
        self.state = 'Rejected'

    def cancel(self):
        """ Payment request will cancel """
        self.state = 'cancelled'

    def validate(self):
        """ Payment request will validte and substarct that amount
        from commission """
        self.state = 'Validated'
        params = request.env['ir.config_parameter'].sudo()
        partner_id = self.env['res.partner'].search(
            [('id', '=', self.seller_id.id)])
        if self.payable_amount < partner_id.commission:
            raise ValidationError(
                _("Entered amount is greater than the commission"))
        product = self.env['ir.config_parameter'].sudo().get_param(
            'multi_vendor_marketplace.pay_product')
        currency = self.env['ir.config_parameter'].sudo().get_param(
            'multi_vendor_marketplace.currency')
        currency_id = self.env['res.currency'].search([('id', '=', currency)])
        self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.seller_id.id,
            'ref': self.seller_id.profile_url,
            'invoice_date': self.date,
            'invoice_payment_term_id': 1,
            'currency_id': currency_id.id,
            'journal_id': 3,
            'invoice_line_ids':
                [(0, 0,
                  {
                      'product_id': product,
                      'name': self.memo,
                      'quantity': 1,
                      'price_unit': self.payable_amount,
                      'currency_id': currency_id.id,
                      'tax_ids': False,
                  })]
        })
        partner_id.commission = partner_id.commission - self.payable_amount

    @api.onchange('seller_id')
    def onchange_seller(self):
        """ For getting default commission"""
        partner_id = self.env['res.partner'].search(
            [('id', '=', self.seller_id.id)])
        self.commission = partner_id.commission

    @api.model
    def create(self, vals):
        """ For getting the sequence number"""
        if vals.get('name', 'New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'seller.payment')
        res = super(SellerPayment, self).create(vals)
        return res
