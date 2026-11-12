from odoo import api, fields, models
from odoo.exceptions import AccessError


class PosElectronicPayment(models.Model):
    _name = "pos.electronic.payment"
    _description = "Point of Sale electronic payment method"
    _inherit = "bus.listener.mixin"

    name = fields.Char(required=True)
    integration_type = fields.Selection(selection=[("terminal", "Terminal"), ("cash_machine", "Cash Machine"), ("qr", "QR Code")], required=True)
    payment_provider = fields.Selection(selection=lambda self: self._get_provider_selection(), required=True, help="Payment provider that will be used to process payments made with this payment method.")

    def _get_terminal_provider_selection(self):
        return []

    def _get_qr_provider_selection(self):
        return []

    def _get_cash_machine_selection(self):
        return []

    def _get_provider_selection(self):
        return self._get_terminal_provider_selection() + self._get_qr_provider_selection() + self._get_cash_machine_selection()

    @api.onchange("integration_type")
    def _onchange_integration_type(self):
        for electronic_payment in self:
            match electronic_payment.integration_type:
                case "terminal":
                    allowed_providers = self._get_terminal_provider_selection()
                case "cash_machine":
                    allowed_providers = self._get_cash_machine_selection()
                case "qr":
                    allowed_providers = self._get_qr_provider_selection()
                case _:
                    allowed_providers = []
            allowed_providers = [value for value, _label in allowed_providers]
            if (electronic_payment.payment_provider not in allowed_providers):
                electronic_payment.payment_provider = False

    @api.onchange("payment_provider")
    def _onchange_payment_provider(self):
        terminal_selection = [value for value, _label in self._get_terminal_provider_selection()]
        qr_selection = [value for value, _label in self._get_qr_provider_selection()]
        cash_machine_selection = [value for value, _label in self._get_cash_machine_selection()]
        for payment_method in self:
            if payment_method.payment_provider in terminal_selection:
                payment_method.integration_type = "terminal"
            elif payment_method.payment_provider in qr_selection:
                payment_method.integration_type = "qr"
            elif payment_method.payment_provider in cash_machine_selection:
                payment_method.integration_type = "cash_machine"

    @api.model
    def get_provider_status(self):
        self._check_access()
        providers = self._get_payment_providers()
        modules = {
            name: self.env["ir.module.module"]._get(provider["module"]) for name, provider in providers.items()
        }
        return {
            name: {**provider, "state": modules[name].state, "id": modules[name].id} for name, provider in providers.items() if modules[name]
        }

    @api.model
    def _get_payment_providers(self) -> dict[str, dict[str, str]]:
        return {
            "adyen": {"type": "terminal", "module": "pos_payment_method_adyen", "name": self.env._("Adyen")},
            "mollie": {"type": "terminal", "module": "pos_payment_method_mollie", "name": self.env._("Mollie")},
            "stripe": {"type": "terminal", "module": "pos_payment_method_stripe", "name": self.env._("Stripe")},
            "sumup": {"type": "terminal", "module": "pos_payment_method_sumup", "name": self.env._("SumUp")},
            "viva_com": {"type": "terminal", "module": "pos_payment_method_viva_com", "name": self.env._("Viva.com")},
            "glory": {"type": "cash_machine", "module": "pos_payment_method_glory", "name": self.env._("Glory")},
            "bank_qr": {"type": "qr", "module": "pos_payment_method_bank_qr", "name": self.env._("Bank QR code")},
        }

    def _notify(self, transaction_id: str, data: dict):
        self._bus_send("pos.electronic.payment", {**data, "transaction_id": transaction_id})

    def _check_access(self):
        if not self.env.su and not self.env.user.has_group("pos_payment_method.group_payment_method_user"):
            raise AccessError(self.env._("You do not have access to make payments"))

    def _check_payment_args(self, amount: float, currency_id: int, extra_args: dict | None):
        currency = self.env["res.currency"].browse(currency_id).exists()
        if not currency:
            msg = "Invalid currency ID"
            raise ValueError(msg)
        amount = currency.round(amount)
        if amount <= 0:
            msg = "Amount must be positive"
            raise ValueError(msg)
        if not extra_args:
            extra_args = {}
        return amount, currency, extra_args

    def _convert_amount_to_units(self, amount: float, currency) -> int:
        return round(amount * 10 ** currency.decimal_places)

    def _convert_units_to_amount(self, amount_units: int, currency) -> float:
        return currency.round(amount_units / (10 ** currency.decimal_places))

    ############################################
    # Public methods for handling transactions #
    ############################################

    def start_payment(self, amount: float, currency_id: int, extra_args: dict | None = None):
        self._check_access()
        self.ensure_one()
        amount, currency, extra_args = self._check_payment_args(amount, currency_id, extra_args)
        return {"status": "pending", **self._start_payment(amount, currency, extra_args)}

    def start_refund(self, amount: float, currency_id: int, extra_args: dict | None = None):
        self._check_access()
        self.ensure_one()
        amount, currency, extra_args = self._check_payment_args(amount, currency_id, extra_args)
        return {"status": "pending", **self._start_refund(amount, currency, extra_args)}

    def start_reversal(self, amount: float, currency_id: int, original_transaction_id: str, extra_args: dict | None = None):
        self._check_access()
        self.ensure_one()
        amount, currency, extra_args = self._check_payment_args(amount, currency_id, extra_args)
        return {"status": "pending", **self._start_reversal(amount, currency, original_transaction_id, extra_args)}

    def adjust_payment(self, amount: float, currency_id: int, transaction_id: str, extra_args: dict | None = None):
        self._check_access()
        self.ensure_one()
        amount, currency, extra_args = self._check_payment_args(amount, currency_id, extra_args)
        return {"status": "pending", **self._adjust_payment(amount, currency, transaction_id, extra_args)}

    def capture_payment(self, amount: float, currency_id: int, transaction_id: str, extra_args: dict | None = None):
        self._check_access()
        self.ensure_one()
        amount, currency, extra_args = self._check_payment_args(amount, currency_id, extra_args)
        return {"status": "pending", **self._capture_payment(amount, currency, transaction_id, extra_args)}

    def cancel_transaction(self, transaction_id: str):
        self._check_access()
        self.ensure_one()
        result = self._cancel_transaction(transaction_id)
        return {**result, "transaction_id": transaction_id}

    def get_transaction_status(self, transaction_id: str):
        self._check_access()
        self.ensure_one()
        result = self._get_transaction_status(transaction_id)
        return {**result, "transaction_id": transaction_id}

    def init_payment_method(self):
        self._check_access()
        self.ensure_one()
        return self._init_payment_method()

    ##################################################
    # Private implementations (per payment provider) #
    ##################################################

    def _start_payment(self, amount: float, currency, extra_args: dict) -> dict:
        raise NotImplementedError

    def _start_refund(self, amount: float, currency, extra_args: dict) -> dict:
        raise NotImplementedError

    def _start_reversal(self, amount: float, currency, original_transaction_id: str, extra_args: dict) -> dict:
        raise NotImplementedError

    def _adjust_payment(self, amount: float, currency, transaction_id: str, extra_args: dict) -> dict:
        raise NotImplementedError

    def _capture_payment(self, amount: float, currency, transaction_id: str, extra_args: dict) -> dict:
        raise NotImplementedError

    def _cancel_transaction(self, transaction_id: str) -> dict:
        raise NotImplementedError

    def _get_transaction_status(self, transaction_id: str) -> dict:
        raise NotImplementedError

    def _init_payment_method(self):
        raise NotImplementedError
