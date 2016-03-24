# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import sets

from openerp import models, fields, api, _

_logger = logging.getLogger(__name__)

class barcode_rule(models.Model):
    _inherit = 'barcode.rule'

    def _get_type_selection(self):
        types = sets.Set(super(barcode_rule, self)._get_type_selection())
        types.update([
            ('credit', _('Credit Card'))
        ])
        return list(types)


class pos_mercury_payment_data(models.Model):
    _name = 'pos_mercury.configuration'

    # FIELDS #
    name = fields.Char(required=True, help='Name of this Mercury configuration')
    merchant_id = fields.Char(string='Merchant ID', required=True, help='ID of the merchant to authenticate him on the payment provider server')
    merchant_pwd = fields.Char(string='Merchant Password', required=True, help='Password of the merchant to authenticate him on the payment provider server')

class account_bank_statement_line(models.Model):
    _inherit = "account.bank.statement.line"

    mercury_card_number = fields.Char(string='Card Number', help='The last 4 numbers of the card used to pay')
    mercury_prefixed_card_number = fields.Char(string='Card Number', compute='_compute_prefixed_card_number', help='The card number used for the payment.')
    mercury_card_brand = fields.Char(string='Card Brand', help='The brand of the payment card (e.g. Visa, AMEX, ...)')
    mercury_card_owner_name = fields.Char(string='Card Owner Name', help='The name of the card owner')
    mercury_ref_no = fields.Char(string='Mercury reference number', help='Payment reference number from Mercury Pay')
    mercury_record_no = fields.Char(string='Mercury record number', help='Payment record number from Mercury Pay')
    mercury_invoice_no = fields.Float(string='Mercury invoice number', help='Invoice number from Mercury Pay')

    @api.one
    def _compute_prefixed_card_number(self):
        if self.mercury_card_number:
            self.mercury_prefixed_card_number = "********" + self.mercury_card_number
        else:
            self.mercury_prefixed_card_number = ""

class account_journal(models.Model):
    _inherit = 'account.journal'

    pos_mercury_config_id = fields.Many2one('pos_mercury.configuration', string='Mercury configuration', help='The configuration of Mercury used for this journal')

class pos_order_card(models.Model):
    _inherit = "pos.order"

    @api.model
    def _payment_fields(self, ui_paymentline):
        fields = super(pos_order_card, self)._payment_fields(ui_paymentline)

        fields.update({
            'card_number': ui_paymentline.get('mercury_card_number'),
            'card_brand': ui_paymentline.get('mercury_card_brand'),
            'card_owner_name': ui_paymentline.get('mercury_card_owner_name'),
            'ref_no': ui_paymentline.get('mercury_ref_no'),
            'record_no': ui_paymentline.get('mercury_record_no'),
            'invoice_no': ui_paymentline.get('mercury_invoice_no')
        })

        return fields

    @api.model
    def add_payment(self, order_id, data):
        statement_id = super(pos_order_card, self).add_payment(order_id, data)
        statement_lines = self.env['account.bank.statement.line'].search([('statement_id', '=', statement_id),
                                                                         ('pos_statement_id', '=', order_id),
                                                                         ('journal_id', '=', data['journal']),
                                                                         ('amount', '=', data['amount'])])

        # we can get multiple statement_lines when there are >1 credit
        # card payments with the same amount. In that case it doesn't
        # matter which statement line we pick, just pick one that
        # isn't already used.
        for line in statement_lines:
            if not line.mercury_card_brand:
                line.mercury_card_brand = data.get('card_brand')
                line.mercury_card_number = data.get('card_number')
                line.mercury_card_owner_name = data.get('card_owner_name')

                line.mercury_ref_no = data.get('ref_no')
                line.mercury_record_no = data.get('record_no')
                line.mercury_invoice_no = data.get('invoice_no')

                break

        return statement_id
