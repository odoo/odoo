import logging
import sets

from openerp import models, fields
_logger = logging.getLogger(__name__)


class barcode_rule(models.Model):
    _inherit = 'barcode.rule'

    def _encoding_selection_list(self):
        selection = sets.Set(super(barcode_rule, self)._encoding_selection_list())
        selection.update([
            ('magnetic_credit', 'magnetic_credit'),
        ])
        print selection
        return list(selection)

    def _get_type_selection(self):
        types = sets.Set(super(barcode_rule, self)._get_type_selection())
        types.update([
            ('Credit', 'Credit Card')
        ])
        return list(types)


class card_reader_payement_data(models.Model):
    _name = 'card_reader.configuration'

    # FIELDS #
    memo = fields.Char(string='Memo', size=40, required=True, help='A custom memo to identify transactions')
    merchant_id = fields.Char(string='Merchant ID', size=24, required=True, help='Id of the merchant to authentify him on the payment provider server')
    merchant_pwd = fields.Char(string='Merchant Password', required=True, help='Password of the merchant to authentify him on the payment provider server')
    payment_server = fields.Char(string='Payment Server', required=True, help='the URL the payment provider server')
    url_base_action = fields.Char(string='Base Action URL', required=True, help='the URL of the SOAP action')


class pos_config(models.Model):
    _inherit = 'pos.config'


class res_users(models.Model):
    _inherit = 'res.users'

    operator_id = fields.Char(string='Default Operator', required=True, size=10, default='test', help='An ID used to identify the operator on transactions')


class account_bank_statement_line(models.Model):
    _inherit = "account.bank.statement.line"

    card_reader_number = fields.Char(string='Card Number', size=20, help='The card number of the card used to paid')
    card_reader_brand = fields.Char(string='Card Brand', size=60, help='The brand of the payment card (e.g. Visa, Maestro, ...)')
    card_reader_name = fields.Char(string='Card Name', help='The name of the card owner')


class account_journal(models.Model):
    _inherit = 'account.journal'

    card_reader_config_id = fields.Many2one('card_reader.configuration', string='Card Reader Config', help='The configuration of the card reader used for this journal')
