# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields

class PosPayment(models.Model):

    _inherit = "pos.payment"

    paytm_authcode = fields.Char('Paytm APPR Code')
    paytm_issuer_card_no = fields.Char('Paytm Issue Mask Card No.')
    paytm_issuer_bank = fields.Char('Paytm Issuer Bank')
    paytm_payment_method = fields.Char('Paytm Payment Method')
    paytm_reference_no = fields.Char('Paytm Merchant Reference No.')
    paytm_card_scheme = fields.Char('Paytm Card Scheme')
