import pprint

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import hash_sign

SUMUP_API_URL = "https://api.sumup.com"


def _sumup_pair_reader(env, merchant_code: str, api_key: str, pairing_code: str, name: str):
    if not merchant_code:
        raise UserError(env._("Please set the SumUp merchant code first."))

    try:
        response = requests.post(
            f"{SUMUP_API_URL}/v0.1/merchants/{merchant_code}/readers",
            json={
                "pairing_code": pairing_code,
                "name": f"Odoo - {name}",
            },
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
    except requests.exceptions.RequestException:
        raise UserError(env._("Could not reach SumUp. Please try again in a moment."))

    if not response.ok:
        try:
            error_detail = response.json().get("detail")
        except ValueError:
            error_detail = None
        raise UserError(
            env._(
                "Could not pair the reader: %(error)s",
                error=error_detail or response.text,
            ),
        )

    return response.json()["id"]


class PosElectronicPayment(models.Model):
    _inherit = "pos.electronic.payment"

    def _get_terminal_provider_selection(self):
        return super()._get_terminal_provider_selection() + [("sumup", "SumUp")]

    sumup_api_key = fields.Char(
        string="SumUp API key",
        help="Used when connecting to SumUp: https://developer.sumup.com/tools/authorization/api-keys#create-an-api-key",
        copy=False,
        groups="pos_payment_method.group_payment_method_admin",
    )
    sumup_merchant_code = fields.Char(
        help="Short unique identifier for the merchant (e.g. MK10CL2A).",
    )

    # Create a new reader on SumUp platform or use an existing one
    sumup_terminal_id = fields.Char(
        string="Reader ID",
        copy=False,
        help="SumUp reader identifier (e.g. rdr_3MSAFM23CK82VSTT4BN6RWSQ65).",
    )
    sumup_pairing_code = fields.Char(
        string="Pairing Code",
        copy=False,
        help="Code displayed on the reader screen, used to pair it once.",
    )

    @api.constrains("sumup_terminal_id")
    def _check_sumup_terminal_id(self):
        for pm in self:
            if not pm.sumup_terminal_id:
                continue
            existing_payment_method = pm.sudo().search(
                [
                    ("id", "!=", pm.id),
                    ("sumup_terminal_id", "=", pm.sumup_terminal_id),
                ],
                limit=1,
            )
            if existing_payment_method:
                raise ValidationError(
                    self.env._(
                        "Reader %(terminal)s is already used on payment method %(payment_method)s.",
                        terminal=pm.sumup_terminal_id,
                        payment_method=existing_payment_method.display_name,
                    ),
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("sumup_pairing_code"):
                vals["sumup_terminal_id"] = _sumup_pair_reader(
                    self.env,
                    vals["sumup_merchant_code"],
                    vals["sumup_api_key"],
                    vals["sumup_pairing_code"],
                    vals["name"],
                )
                vals["sumup_pairing_code"] = False
        return super().create(vals_list)

    def write(self, vals):
        if not vals.get("sumup_pairing_code"):
            return super().write(vals)

        for payment_method in self:
            record_vals = dict(vals)
            record_vals["sumup_terminal_id"] = _sumup_pair_reader(
                self.env,
                record_vals.get(
                    "sumup_merchant_code",
                    payment_method.sumup_merchant_code,
                ),
                record_vals.get("sumup_api_key", payment_method.sudo().sumup_api_key),
                record_vals["sumup_pairing_code"],
                payment_method.display_name,
            )
            record_vals["sumup_pairing_code"] = False
            super(PosElectronicPayment, payment_method).write(record_vals)
        return True

    def _sumup_get_error_message(self, response: requests.Response):
        try:
            errors = response.json().get("errors")
            if not errors:
                error_detail = None
            elif "detail" in errors:
                error_detail = errors["detail"]
            else:
                error_detail = self.env._("SumUp returned the following errors:\n%s", pprint.pformat(errors))
        except ValueError:
            error_detail = None
        return error_detail or response.text

    def _sumup_resolve_transaction_id(self, client_transaction_id: str):
        """Resolve the real SumUp transaction id for a completed checkout.

        Neither the webhook notification nor the reader-checkout status endpoint
        provide it.
        """
        self.ensure_one()
        try:
            response = requests.get(
                f"{SUMUP_API_URL}/v2.1/merchants/{self.sumup_merchant_code}/transactions",
                headers={"Authorization": f"Bearer {self.sudo().sumup_api_key}"},
                params={"client_transaction_id": client_transaction_id},
                timeout=10,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException:
            return False
        return response.json().get("id")

    def _sumup_notification_url(self):
        """Build the return_url passed to SumUp, carrying a signed reference to this
        payment method so that the notification webhook can be routed back to the exact
        reader
        """
        self.ensure_one()
        token = hash_sign(
            self.sudo().env,
            "pos_sumup",
            {"payment_method_id": self.id},
            expiration_hours=1,
        )
        return f"{self.get_base_url()}/pos_sumup/notification?token={token}"

    def _start_payment(self, amount: float, currency, extra_args: dict):
        if self.payment_provider != "sumup":
            return super()._start_payment(amount, currency, extra_args)
        minor_amount = self._convert_amount_to_units(amount, currency)
        try:
            response = requests.post(
                f"{SUMUP_API_URL}/v0.1/merchants/{self.sumup_merchant_code}/readers/{self.sumup_terminal_id}/checkout",
                headers={"Authorization": f"Bearer {self.sudo().sumup_api_key}"},
                json={
                    "total_amount": {
                        "currency": currency.name,
                        "minor_unit": currency.decimal_places,
                        "value": minor_amount,
                    },
                    "return_url": self._sumup_notification_url(),
                },
                timeout=10,
            )
        except requests.exceptions.RequestException:
            return {"error": self.env._("Could not reach SumUp. Please try again.")}
        if not response.ok:
            return {"error": self._sumup_get_error_message(response)}

        body = response.json()
        return {"transaction_id": body["data"]["client_transaction_id"]}

    def _start_reversal(self, amount: float, currency, original_transaction_id: str, extra_args: dict):
        if self.payment_provider != "sumup":
            return super()._start_reversal(amount, currency, original_transaction_id, extra_args)

        transaction_id = self._sumup_resolve_transaction_id(original_transaction_id)
        if not transaction_id:
            raise UserError(
                self.env._("Couldn't find a transaction corresponding to this payment."),
            )

        try:
            response = requests.post(
                f"{SUMUP_API_URL}/v1.0/merchants/{self.sumup_merchant_code}/payments/{transaction_id}/refunds",
                headers={"Authorization": f"Bearer {self.sudo().sumup_api_key}"},
                json={
                    "amount": self._convert_amount_to_units(amount, currency),
                },
                timeout=10,
            )
        except requests.exceptions.RequestException:
            return {"error": self.env._("Could not reach SumUp. Please try again.")}
        if not response.ok:
            return {"error": self._sumup_get_error_message(response)}

        return {"status": "paid", "transaction_id": transaction_id}

    def _get_transaction_status(self, transaction_id: str):
        if self.payment_provider != "sumup":
            return super()._get_transaction_status(transaction_id)

        try:
            response = requests.get(
                f"{SUMUP_API_URL}/v2.1/merchants/{self.sumup_merchant_code}/transactions",
                headers={"Authorization": f"Bearer {self.sudo().sumup_api_key}"},
                params={"client_transaction_id": transaction_id},
                timeout=10,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException:
            return {"status": "pending"}

        data = response.json()
        sumup_status = data["status"]
        if sumup_status in ["SUCCESSFUL", "REFUNDED"]:
            return {"status": "paid"}
        if sumup_status in ["FAILED", "CANCELLED"]:
            return {"status": "failed"}
        return {"status": "pending"}

    def _cancel_transaction(self, transaction_id: str):
        if self.payment_provider != "sumup":
            return super()._cancel_transaction(transaction_id)

        try:
            response = requests.post(
                f"{SUMUP_API_URL}/v0.1/merchants/{self.sumup_merchant_code}/readers/{self.sumup_terminal_id}/terminate",
                headers={"Authorization": f"Bearer {self.sudo().sumup_api_key}"},
                timeout=10,
            )
        except requests.exceptions.RequestException:
            return {"error": self.env._("Could not reach SumUp. Please try again.")}
        if not response.ok:
            return {"error": self._sumup_get_error_message(response)}
        return {}
