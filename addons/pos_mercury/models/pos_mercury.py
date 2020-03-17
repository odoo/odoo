# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class BarcodeRule(models.Model):
    _inherit = 'barcode.rule'

    type = fields.Selection(selection_add=[
        ('credit', 'Credit Card')
    ], ondelete={'credit': 'set default'})


class PosMercuryConfiguration(models.Model):
    _name = 'pos_mercury.configuration'
    _description = 'Point of Sale Vantiv Configuration'

    name = fields.Char(required=True, help='Name of this Vantiv configuration')
    merchant_id = fields.Char(string='Merchant ID', required=True, help='ID of the merchant to authenticate him on the payment provider server')
    merchant_pwd = fields.Char(string='Merchant Password', required=True, help='Password of the merchant to authenticate him on the payment provider server')


class PoSPayment(models.Model):
    _inherit = "pos.payment"

    mercury_card_number = fields.Char(string='Card Number', help='The last 4 numbers of the card used to pay')
    mercury_prefixed_card_number = fields.Char(string='Card Number Prefix', compute='_compute_prefixed_card_number', help='The card number used for the payment.')
    mercury_card_brand = fields.Char(string='Card Brand', help='The brand of the payment card (e.g. Visa, AMEX, ...)')
    mercury_card_owner_name = fields.Char(string='Card Owner Name', help='The name of the card owner')
    mercury_ref_no = fields.Char(string='Vantiv reference number', help='Payment reference number from Vantiv Pay')
    mercury_record_no = fields.Char(string='Vantiv record number', help='Payment record number from Vantiv Pay')
    mercury_invoice_no = fields.Char(string='Vantiv invoice number', help='Invoice number from Vantiv Pay')

    def _compute_prefixed_card_number(self):
        for line in self:
            if line.mercury_card_number:
                line.mercury_prefixed_card_number = "********" + line.mercury_card_number
            else:
                line.mercury_prefixed_card_number = ""


class PoSPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    pos_mercury_config_id = fields.Many2one('pos_mercury.configuration', string='Vantiv Credentials', help='The configuration of Vantiv used for this journal')

    def _get_payment_terminal_selection(self):
        return super(PoSPaymentMethod, self)._get_payment_terminal_selection() + [('mercury', 'Vantiv')]

    @api.onchange('use_payment_terminal')
    def _onchange_use_payment_terminal(self):
        super(PoSPaymentMethod, self)._onchange_use_payment_terminal()
        if self.use_payment_terminal != 'mercury':
            self.pos_mercury_config_id = False

class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.model
    def _payment_fields(self, order, ui_paymentline):
        fields = super(PosOrder, self)._payment_fields(order, ui_paymentline)

        fields.update({
            'mercury_card_number': ui_paymentline.get('mercury_card_number'),
            'mercury_card_brand': ui_paymentline.get('mercury_card_brand'),
            'mercury_card_owner_name': ui_paymentline.get('mercury_card_owner_name'),
            'mercury_ref_no': ui_paymentline.get('mercury_ref_no'),
            'mercury_record_no': ui_paymentline.get('mercury_record_no'),
            'mercury_invoice_no': ui_paymentline.get('mercury_invoice_no')
        })

        return fields
