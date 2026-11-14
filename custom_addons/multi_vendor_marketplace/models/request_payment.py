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


class RequestPayment(models.Model):
    """Create a RequestPayment class for request for payment"""
    _name = 'request.payment'

    seller_id = fields.Many2one('res.partner', string='Seller',
                                required=True, help='Seller', default=lambda
                                self: self.env.user.partner_id.id)
    cashable_amount = fields.Float(string='Commission', help='Commission',
                                   readonlt=True)
    request_amount = fields.Float(string='Requested Payment Amount',
                                  help='Requested Amount', required=True)
    payment_description = fields.Text(string='Payment Description',
                                      help='Payment Description',
                                      required=True)

    @api.onchange('seller_id')
    def onchange_seller(self):
        """ Display commission in seller profile tab """
        partner_id = self.env['res.partner'].browse(self.seller_id.id)
        self.cashable_amount = partner_id.commission

    def request_payment(self):
        """ Request payment """
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
            if (self.request_amount > partner_id.total_commission or
                    self.request_amount > int(amount_limit) or
                    checkdate.date >= mingap_date):
                raise ValidationError(
                    _("Entered amount is greater than your commission or "
                      "Amount limit is " + amount_limit + " and Minimum gap "
                                                          "for next payment "
                                                          "request " +
                      min_gap + " days"))
            break
        self.env['seller.payment'].create({
            'seller_id': self.seller_id.id,
            'payment_mode': 'Cash',
            'commission': partner_id.commission,
            'payable_amount': self.request_amount,
            'date': fields.Date.today(),
            'type_id': 1,
            'memo': self.payment_description,
            'state': 'Requested',
        })
