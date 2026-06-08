from odoo import fields, models


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    cashmatic_ip = fields.Char('Cashmatic IP')
    cashmatic_username = fields.Char('Cashmatic Username')
    cashmatic_password = fields.Char('Cashmatic Password')
    cashmatic_use_lna = fields.Boolean('Cashmatic Local Network Access')

    def _get_cash_machine_selection(self):
        return super()._get_cash_machine_selection() + [('cashmatic', 'Cash Machine (cashmatic)')]

    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ['cashmatic_ip', 'cashmatic_username', 'cashmatic_password', 'cashmatic_use_lna']
