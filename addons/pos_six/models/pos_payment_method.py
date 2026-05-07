from odoo import fields, models, api


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_terminal_provider_selection(self):
        return super()._get_terminal_provider_selection() + [('six', 'SIX')]

    six_terminal_ip = fields.Char('Six Terminal IP')

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ['six_terminal_ip']
        return params
