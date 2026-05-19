# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain

from odoo.addons.payment_custom import const


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    _custom_providers_setup = models.Constraint(
        "CHECK(custom_mode IS NULL OR (code = 'custom' AND custom_mode IS NOT NULL))",
        "Only custom providers should have a custom mode.",
    )

    code = fields.Selection(
        selection_add=[("custom", "Custom")], ondelete={"custom": "set default"}
    )
    custom_mode = fields.Selection(
        string="Custom Mode",
        selection=[("wire_transfer", "Wire Transfer")],
        required_if_provider="custom",
    )
    qr_code = fields.Boolean(
        string="Enable QR Codes", help="Enable the use of QR-codes when paying by wire transfer."
    )

    # === CRUD METHODS ===#

    def _check_required_if_provider(self):
        """Check that `bank_account_id` have been filled for wire transfer provider."""
        if "bank_account_id" not in self._fields:
            return super()._check_required_if_provider()

        wire_transfer_without_bank = self.filtered(
            lambda provider: (
                provider.custom_mode == "wire_transfer"
                and provider.state != "disabled"
                and not provider.bank_account_id
            )
        )
        if wire_transfer_without_bank:
            raise ValidationError(self.env._("Bank account must be filled for Wire Transfer."))

        super()._check_required_if_provider()

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        self.ensure_one()
        if self.code != "custom" or self.custom_mode != "wire_transfer":
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === BUSINESS METHODS === #

    def _get_custom_provider_bank_details(self):
        """Return bank details configured on the provider.

        :return: A dictionary containing the beneficiary name and bank account number.
        :rtype: dict
        """
        if bank_account := self._get_custom_bank_account():
            return {
                "beneficiary": bank_account.holder_name,
                "bank_account": bank_account.display_name,
            }
        return {}

    def _get_custom_bank_account(self):
        """Return the bank account configured on the custom provider.

        :return: The bank account of the provider.
        :rtype: record of `res.partner.bank` or None
        """
        if (
            self.custom_mode in self._get_custom_bank_related_modes()
            and "bank_account_id" in self._fields
        ):
            return self.bank_account_id

    @api.model
    def _get_custom_bank_related_modes(self):
        """Return custom modes that rely on bank details.

        :return: The list of custom modes.
        :rtype: list
        """
        return ["wire_transfer"]

    def _get_custom_qr_bank_account(self):
        """Return the bank account used to generate QR codes for custom providers."""
        return self._get_custom_bank_account() or self.company_id.partner_id.bank_ids[:1]

    # === SETUP METHODS === #

    @api.model
    def _get_provider_domain(self, provider_code, *, custom_mode="", **kwargs):
        res = super()._get_provider_domain(provider_code, custom_mode=custom_mode, **kwargs)
        if provider_code == "custom" and custom_mode:
            return Domain.AND([res, [("custom_mode", "=", custom_mode)]])
        return res

    @api.model
    def _get_removal_values(self):
        """Override of `payment` to nullify the `custom_mode` field."""
        res = super()._get_removal_values()
        res["custom_mode"] = None
        return res
