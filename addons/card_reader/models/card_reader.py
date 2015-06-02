import logging
import sets
import time

from openerp import models, fields, api

_logger = logging.getLogger(__name__)

class barcode_rule(models.Model):
    _inherit = 'barcode.rule'

    def _get_type_selection(self):
        types = sets.Set(super(barcode_rule, self)._get_type_selection())
        types.update([
            ('Credit', 'Credit Card')
        ])
        return list(types)


class card_reader_payment_data(models.Model):
    _name = 'card_reader.configuration'

    # FIELDS #
    memo = fields.Char(string='Memo', size=40, required=True, help='A custom memo to identify transactions')
    merchant_id = fields.Char(string='Merchant ID', size=24, required=True, help='Id of the merchant to authentify him on the payment provider server')
    merchant_pwd = fields.Char(string='Merchant Password', required=True, help='Password of the merchant to authentify him on the payment provider server')
    payment_server = fields.Char(string='Payment Server', required=True, help='the URL the payment provider server')
    url_base_action = fields.Char(string='Base Action URL', required=True, help='the URL of the SOAP action')


class account_bank_statement_line(models.Model):
    _inherit = "account.bank.statement.line"

    card_number = fields.Char(string='Card Number', size=4, help='The last 4 numbers of the card used to pay')
    prefixed_card_number = fields.Char(string='Card Number', compute='_compute_prefixed_card_number')
    card_brand = fields.Char(string='Card Brand', help='The brand of the payment card (e.g. Visa, Maestro, ...)')
    card_owner_name = fields.Char(string='Card Owner Name', help='The name of the card owner')
    ref_no = fields.Char(string='Mercury reference number')
    record_no = fields.Char(string='Mercury record number')
    invoice_no = fields.Integer(string='Mercury invoice number')

    @api.one
    def _compute_prefixed_card_number(self):
        if self.card_number:
            self.prefixed_card_number = "********" + self.card_number
        else:
            self.prefixed_card_number = ""

class account_journal(models.Model):
    _inherit = 'account.journal'

    card_reader_config_id = fields.Many2one('card_reader.configuration', string='Card Reader Config', help='The configuration of the card reader used for this journal')

class pos_order_card(models.Model):
    _inherit = "pos.order"

    @api.model
    def _payment_fields(self, ui_paymentline):
        fields = super(pos_order_card, self)._payment_fields(ui_paymentline)

        fields.update({
            'card_number': ui_paymentline.get('card_number'),
            'card_brand': ui_paymentline.get('card_brand'),
            'card_owner_name': ui_paymentline.get('card_owner_name'),
            'ref_no': ui_paymentline.get('ref_no'),  # todo jov
            'record_no': ui_paymentline.get('record_no'),  # todo jov
            'invoice_no': ui_paymentline.get('invoice_no')
        })

        return fields

    @api.model
    def add_payment(self, order_id, data):
        statement_id = super(pos_order_card, self).add_payment(order_id, data)
        statement_line = self.env['account.bank.statement.line'].search([('statement_id', '=', statement_id),
                                                                         ('pos_statement_id', '=', order_id),
                                                                         ('journal_id', '=', data['journal']),
                                                                         ('amount', '=', data['amount'])])
        statement_line.card_number = data.get('card_number')
        statement_line.card_brand = data.get('card_brand')
        statement_line.card_owner_name = data.get('card_owner_name')

        # todo jov: this needs some work in that we can only keep most
        # recent record_no and we need to delete after 6 months
        statement_line.ref_no = data.get('ref_no')
        statement_line.record_no = data.get('record_no')
        statement_line.invoice_no = data.get('invoice_no')

        return statement_id

    @api.multi
    def refund(self):
        abs = super(pos_order_card, self).refund()

        for order in self.browse(self.ids):
            for statement_line in order.statement_ids:
                if statement_line.card_brand:
                    response = self.env['card_reader.mercury_transaction'].do_return({'transaction_type': 'Credit', 'transaction_code': 'ReturnByRecordNo',
                                                                                      'ref_no': statement_line.ref_no, 'record_no': statement_line.record_no,
                                                                                      'invoice_no': statement_line.invoice_no, 'purchase': statement_line.amount,
                                                                                      'journal_id': statement_line.journal_id.id}, self.user_id.id)

                    if "<TextResponse>AP</TextResponse>" in response:
                        order = self.env['pos.order'].browse(abs['res_id'])

                        data = {
                            'amount': order.amount_total - order.amount_paid,
                            'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'journal': statement_line.journal_id.id,
                            'card_number': statement_line.card_number,
                            'card_brand': statement_line.card_brand,
                            'card_owner_name': statement_line.card_owner_name
                        }

                        if data['amount'] != 0.0:
                            order.add_payment(abs['res_id'], data)

                        order.signal_workflow('paid')
                    elif "<TextResponse>AP*</TextResponse>" in response:
                        _logger.warning("Mercury credit card return was NOT approved because it was a duplicate return.")
                    else:
                        _logger.error("Mercury credit card return was NOT approved.")
        return abs
