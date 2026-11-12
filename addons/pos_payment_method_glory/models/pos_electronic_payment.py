import random
import string

from odoo import fields, models


class PosElectronicPayment(models.Model):
    _inherit = "pos.electronic.payment"

    glory_websocket_address = fields.Char("Cash Machine IP")
    glory_username = fields.Char("Cash Machine Username")
    glory_password = fields.Char("Cash Machine Password")
    glory_use_lna = fields.Boolean("Cash Machine Local Network Access")

    def _get_cash_machine_selection(self):
        return super()._get_cash_machine_selection() + [("glory", "Glory")]

    def _glory_generate_sequence_number(self):
        return "".join(random.choices(string.ascii_letters + string.digits, k=11))

    def _glory_transaction_details(self, amount: float, currency, is_refund: bool):
        amount_units = self._convert_amount_to_units(amount, currency)
        return {
            "transaction_id": self._glory_generate_sequence_number(),
            "currency_decimals": currency.decimal_places,
            "amount_units": -amount_units if is_refund else amount_units,
        }

    def _init_payment_method(self):
        if self.payment_provider != "glory":
            return super()._init_payment_method()
        return {
            "glory_ip": self.glory_websocket_address,
            "glory_username": self.glory_username,
            "glory_password": self.glory_password,
            "glory_use_lna": self.glory_use_lna,
        }

    def _start_payment(self, amount: float, currency, extra_args: dict):
        if self.payment_provider != "glory":
            return super()._start_payment(amount, currency, extra_args)

        return self._glory_transaction_details(amount, currency, is_refund=False)

    def _start_refund(self, amount: float, currency, extra_args: dict):
        if self.payment_provider != "glory":
            return super()._start_payment(amount, currency, extra_args)

        return self._glory_transaction_details(amount, currency, is_refund=True)
