from odoo import api, models


class PaymentOptions(models.Model):
    _name = 'l10n_co_edi.payment.option'
    _inherit = ['l10n_co_edi.payment.option', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['name']

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', 'in', [order['l10n_co_edi_pos_payment_option_id'] for order in data['pos.order']['data']])]
