from odoo import api, fields, models


class PosElectronicPayment(models.Model):
    _inherit = "pos.electronic.payment"

    stripe_payment_provider_id = fields.Many2one("payment.provider", domain=[("code", "=", "stripe")])
    stripe_secret_key = fields.Char(related="stripe_payment_provider_id.stripe_secret_key", related_sudo=False, groups="pos_payment_method.group_payment_method_admin")
    stripe_serial_number = fields.Char(help="[Serial number of the Stripe terminal], for example: WSC513105011295", copy=False)
    stripe_ask_customer_for_tip = fields.Boolean("Ask For Tips on Terminal")

    def _get_terminal_provider_selection(self):
        return super()._get_terminal_provider_selection() + [("stripe", "Stripe")]

    @api.onchange("stripe_secret_key")
    def _onchange_stripe_secret_key(self):
        for record in self:
            if record.stripe_payment_provider_id:
                record.stripe_payment_provider_id.stripe_secret_key = record.stripe_secret_key

    def _get_payment_method_details_from_stripe_payment(self, payment_intent: dict) -> dict:
        charge_id = payment_intent["latest_charge"]
        charge = next(charge for charge in payment_intent["charges"]["data"] if charge["id"] == charge_id)
        payment_type = charge["payment_method_details"]["type"]
        return charge["payment_method_details"][payment_type]

    def _init_payment_method(self):
        if self.payment_provider != "stripe":
            return super()._init_payment_method()
        return self.stripe_payment_provider_id._send_api_request("POST", "terminal/connection_tokens")

    def _start_payment(self, amount: float, currency, extra_args: dict):
        if self.payment_provider != "stripe":
            return super()._start_payment(amount, currency, extra_args)

        params = [
            ("currency", currency.name),
            ("amount", self._convert_amount_to_units(amount, currency)),
            ("payment_method_types[]", "card_present"),
            ("capture_method", "manual" if extra_args.get("allow_adjustments") else "automatic_async"),
            ("metadata[allow_tips]", "true" if extra_args.get("allow_tips") and self.stripe_ask_customer_for_tip else ""),
        ]

        if currency.name == "AUD" and self.env.company.country_code == "AU" and extra_args.get("allow_adjustments"):
            # See https://stripe.com/docs/terminal/payments/regional?integration-country=AU
            # This parameter overrides "capture_method": "manual" above.
            params.append(("payment_method_options[card_present][capture_method]", "manual_preferred"))
        if currency.name == "CAD" and self.env.company.country_code == "CA":
            params.append(("payment_method_types[]", "interac_present"))

        response = self.stripe_payment_provider_id._send_api_request("POST", "payment_intents", data=params)
        return {
            "transaction_id": response["id"],
            "client_secret": response["client_secret"],
            "terminal_serial_number": self.stripe_serial_number,
            "allow_tips": bool(extra_args.get("allow_tips")),
        }

    def _adjust_payment(self, amount: float, currency, transaction_id: str, extra_args: dict):
        if self.payment_provider != "stripe":
            return super()._adjust_payment(amount, currency, transaction_id, extra_args)

        return {
            **self._capture_payment(amount, currency, transaction_id, extra_args),
            "metadata": {"can_be_adjusted": False},
        }

    def _capture_payment(self, amount: float, currency, transaction_id: str, extra_args: dict):
        if self.payment_provider != "stripe":
            return super()._capture_payment(amount, currency, transaction_id, extra_args)

        data = {
            "amount_to_capture": self._convert_amount_to_units(amount, currency),
        }

        self.stripe_payment_provider_id._send_api_request("POST", f"payment_intents/{transaction_id}/capture", data=data)
        return {"status": "paid", "transaction_id": transaction_id}

    def _start_reversal(self, amount: float, currency, original_transaction_id: str, extra_args: dict):
        if self.payment_provider != "stripe":
            return super()._start_reversal(amount, currency, original_transaction_id, extra_args)

        params = [
            ("payment_intent", original_transaction_id),
            ("amount", self._convert_amount_to_units(amount, currency)),
        ]

        response = self.stripe_payment_provider_id._send_api_request("POST", "refunds", data=params)
        if response["status"] == "succeeded":
            return {"transaction_id": response["id"], "status": "paid"}
        if response["status"] in ["failed", "canceled"]:
            return {"transaction_id": response["id"], "status": "failed"}
        return {"transaction_id": response["id"], "status": "pending"}

    def _get_transaction_status(self, transaction_id: str):
        if self.payment_provider != "stripe":
            return super()._get_transaction_status(transaction_id)

        response = self.stripe_payment_provider_id._send_api_request("GET", f"payment_intents/{transaction_id}")
        if response["status"] in ("requires_capture", "succeeded"):
            payment_details = self._get_payment_method_details_from_stripe_payment(response)
            tip = response["amount_details"].get("tip", {}).get("amount", 0)
            currency = self.env['res.currency'].search([('name', '=ilike', response["currency"])], limit=1)
            return {
                "status": "paid",
                "card_type": payment_details["brand"],
                "tip_amount": self._convert_units_to_amount(tip, currency),
                "metadata": {
                    "requires_capture": response["status"] == "requires_capture",
                    "can_be_adjusted": response["status"] == "requires_capture" and payment_details["overcapture_supported"],
                },
            }
        if response["status"] == "canceled":
            return {"status": "failed"}
        return {
            "status": "pending",
            "stripe_status": response["status"],
            "client_secret": response["client_secret"],
            "terminal_serial_number": self.stripe_serial_number,
            "allow_tips": bool(response["metadata"].get("allow_tips")),
        }
