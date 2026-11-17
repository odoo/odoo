from odoo import fields, models


class PosPaymentMethod(models.Model):
    _inherit = "pos.electronic.payment"

    cashdro_ip = fields.Char("Cashdro IP")
    cashdro_username = fields.Char("Cashdro Username")
    cashdro_password = fields.Char("Cashdro Password")
    cashdro_use_lna = fields.Boolean("Cashdro Local Network Access")

    def _get_cash_machine_selection(self):
        return super()._get_cash_machine_selection() + [("cashdro", "Cashdro")]

    def _init_payment_method(self):
        if self.payment_provider != "cashdro":
            return super()._init_payment_method()

        return {
            "cashdro_ip": self.cashdro_ip,
            "cashdro_username": self.cashdro_username,
            "cashdro_password": self.cashdro_password,
            "cashdro_use_lna": self.cashdro_use_lna,
        }
