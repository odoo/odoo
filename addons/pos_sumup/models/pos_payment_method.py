import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import hash_sign

_logger = logging.getLogger(__name__)

SUMUP_API_URL = "https://api.sumup.com"


def _sumup_pair_reader(merchant_code: str, api_key: str, pairing_code: str, name: str):
    if not merchant_code:
        raise UserError(_("Please set the SumUp merchant code first."))

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
        raise UserError(_("Could not reach SumUp. Please try again in a moment."))

    if not response.ok:
        try:
            error_detail = response.json().get("detail")
        except ValueError:
            error_detail = None
        raise UserError(
            _(
                "Could not pair the reader: %(error)s",
                error=error_detail or response.text,
            ),
        )

    return response.json()["id"]


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def _get_terminal_provider_selection(self):
        return super()._get_terminal_provider_selection() + [("sumup", "SumUp")]

    # SumUp
    sumup_api_key = fields.Char(
        string="SumUp API key",
        help="Used when connecting to SumUp: https://developer.sumup.com/tools/authorization/api-keys#create-an-api-key",
        copy=False,
        groups="base.group_erp_manager",
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
                if existing_payment_method.company_id == pm.company_id:
                    raise ValidationError(
                        _(
                            "Reader %(terminal)s is already used on payment method %(payment_method)s.",
                            terminal=pm.sumup_terminal_id,
                            payment_method=existing_payment_method.display_name,
                        ),
                    )
                raise ValidationError(
                    _(
                        "Reader %(terminal)s is already used in company %(company)s on payment method %(payment_method)s.",
                        terminal=pm.sumup_terminal_id,
                        company=existing_payment_method.company_id.name,
                        payment_method=existing_payment_method.display_name,
                    ),
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("sumup_pairing_code"):
                vals["sumup_terminal_id"] = _sumup_pair_reader(
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
                record_vals.get(
                    "sumup_merchant_code",
                    payment_method.sumup_merchant_code,
                ),
                record_vals.get("sumup_api_key", payment_method.sudo().sumup_api_key),
                record_vals["sumup_pairing_code"],
                payment_method.display_name,
            )
            record_vals["sumup_pairing_code"] = False
            super(PosPaymentMethod, payment_method).write(record_vals)
        return True

    def sumup_get_checkout_status(self, checkout_id: str):
        """Ask SumUp directly for the current status of a reader checkout.
        Used as a polling fallback for the initial payment, in case the
        SUMUP_LATEST_RESPONSE bus notification is missed."""
        self.ensure_one()
        try:
            response = requests.get(
                f"{SUMUP_API_URL}/v0.1/merchants/{self.sumup_merchant_code}/readers/{self.sumup_terminal_id}/checkout/{checkout_id}",
                headers={"Authorization": f"Bearer {self.sudo().sumup_api_key}"},
                timeout=10,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException:
            return False
        return response.json()

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

    def sumup_pay(self, amount: float):
        self.ensure_one()
        currency = self.journal_id.currency_id or self.company_id.currency_id
        minor_unit = currency.decimal_places
        minor_amount = round(amount * (10**minor_unit))
        try:
            response = requests.post(
                f"{SUMUP_API_URL}/v0.1/merchants/{self.sumup_merchant_code}/readers/{self.sumup_terminal_id}/checkout",
                headers={"Authorization": f"Bearer {self.sudo().sumup_api_key}"},
                json={
                    "total_amount": {
                        "currency": currency.name,
                        "minor_unit": minor_unit,
                        "value": minor_amount,
                    },
                    "return_url": self._sumup_notification_url(),
                },
                timeout=10,
            )
        except requests.exceptions.RequestException:
            return {"error": {"message": _("Could not reach SumUp. Please try again.")}}

        if not response.ok:
            try:
                error_detail = response.json().get("errors").get("detail")
            except ValueError:
                error_detail = None
            return {
                "error": {
                    "status_code": response.status_code,
                    "message": error_detail or response.text,
                },
            }

        return response.json()

    def sumup_refund(self, amount: float, client_transaction_id: str):
        self.ensure_one()
        original_payment = client_transaction_id and self.env["pos.payment"].search(
            [
                ("transaction_id", "=", client_transaction_id),
                ("payment_method_id.payment_provider", "=", "sumup"),
            ],
            limit=1,
        )
        if not original_payment:
            raise UserError(_("SumUp can't refund a transaction not paid with SumUp."))
        currency = self.journal_id.currency_id or self.company_id.currency_id
        amount = abs(round(amount * (10**currency.decimal_places)))
        transaction_id = self._sumup_resolve_transaction_id(client_transaction_id)
        if not transaction_id:
            raise UserError(
                _("Couldn't find a transaction corresponding to this payment."),
            )
        response = requests.post(
            f"{SUMUP_API_URL}/v1.0/merchants/{self.sumup_merchant_code}/payments/{transaction_id}/refunds",
            headers={"Authorization": f"Bearer {self.sudo().sumup_api_key}"},
            json={
                "amount": amount,
            },
            timeout=10,
        )
        return response.json()

    def sumup_cancel(self):
        try:
            response = requests.post(
                f"{SUMUP_API_URL}/v0.1/merchants/{self.sumup_merchant_code}/readers/{self.sumup_terminal_id}/terminate",
                headers={"Authorization": f"Bearer {self.sudo().sumup_api_key}"},
                json={
                    "return_url": self._sumup_notification_url(),
                },
                timeout=10,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException:
            raise UserError(_("Could not reach SumUp. Please try again."))
        return True
