from odoo import fields, models


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    cashdro_ip = fields.Char('Cashdro IP')
    cashdro_username = fields.Char('Cashdro Username')
    cashdro_password = fields.Char('Cashdro Password')
    cashdro_use_lna = fields.Boolean('Cashdro Local Network Access')

    def _get_cash_machine_selection(self):
        return super()._get_cash_machine_selection() + [('cashdro', 'Cashdro')]

    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ['cashdro_ip', 'cashdro_username', 'cashdro_password', 'cashdro_use_lna']
