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
    merchant_id = fields.Char(string='Merchant ID', size=24, required=True)
    merchant_pwd = fields.Char(string='Merchant Password', required=True)
    memo = fields.Char(string='Memo', size=40, required=True)
    payment_server = fields.Char(string='Payment Server', required=True)
    url_base_action = fields.Char(string='Base Action URL', required=True)


class pos_config(models.Model):
    _inherit = 'pos.config'

    card_reader = fields.Boolean(string='activate electronic card payment')
    operator_id = fields.Char(string='Default Operator', required=True, size=10, default='Operator 1')
    card_reader_config_id = fields.Many2one('card_reader.configuration', string='Card Reader Config')
