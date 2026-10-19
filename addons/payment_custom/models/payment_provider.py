# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
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
        selection=[("pay_on_invoice", "Pay on Invoice"), ("wire_transfer", "Wire Transfer")],
        required_if_provider="custom",
    )
    qr_code = fields.Boolean(
        string="Enable QR Codes", help="Enable the use of QR-codes when paying by wire transfer."
    )
    company_partner_id = fields.Many2one(
        comodel_name="res.partner", related="company_id.partner_id"
    )
    partner_bank_id = fields.Many2one(
        string="Bank Account",
        comodel_name="res.partner.bank",
        domain='[("partner_id", "=", company_partner_id)]',
        compute="_compute_partner_bank_id",
        store=True,
        readonly=False,
        copy=False,
        check_company=True,
    )

    # === COMPUTE METHODS === #

    @api.depends("company_id")
    def _compute_partner_bank_id(self):
        for provider in self:
            provider.partner_bank_id = provider.company_id.partner_id.bank_ids[:1]

    # === CRUD METHODS ===#

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        if self.custom_mode != "wire_transfer":
            return vals_list

        for vals in vals_list:
            vals["is_live"] = True
        return vals_list

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        self.ensure_one()
        if self.custom_mode not in ["pay_on_invoice", "wire_transfer"]:
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === BUSINESS METHODS === #

    def _get_custom_bank_account(self):
        """Return the bank account to display in the pending payment instructions template.

        :return: The bank account of the provider.
        :rtype: res.partner.bank
        """
        if self.custom_mode == "wire_transfer":
            return self.partner_bank_id
        return self.env["res.partner.bank"]

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
