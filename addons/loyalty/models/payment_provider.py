# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from odoo.addons.loyalty.const import LOYALTY_PAYMENT_CODES


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("gift_card", "Gift Card"), ("ewallet", "eWallet")],
        ondelete={"gift_card": "set default", "ewallet": "set default"},
    )
    # Loyalty providers are only published when an active program of the matching type exists.
    is_published = fields.Boolean(compute="_compute_is_published", store=True, readonly=False)

    # === COMPUTE METHODS === #

    @api.depends("code", "company_id")
    def _compute_is_published(self):
        """Publish loyalty providers only if an active program of the same type exists.

        The publication of other providers is left untouched. The recomputation is also triggered by
        `loyalty.program` when programs are created, (un)archived, or deleted.
        """
        published_codes_per_company = self._get_loyalty_published_codes_per_company()
        for provider in self:
            if provider.code in LOYALTY_PAYMENT_CODES:
                provider.is_published = provider.code in published_codes_per_company.get(
                    provider.company_id.id, set()
                ) | published_codes_per_company.get(False, set())
            else:
                provider.is_published = provider.is_published

    def _get_loyalty_published_codes_per_company(self):
        """Return the loyalty program types that have an active program, per company.

        :return: The program types with at least one active program, per company id (or `False` for
                 programs shared between companies).
        :rtype: dict
        """
        if not any(code in LOYALTY_PAYMENT_CODES for code in self.mapped("code")):
            return {}
        programs_data = (
            self
            .env["loyalty.program"]
            .sudo()
            ._read_group(
                domain=[("program_type", "in", LOYALTY_PAYMENT_CODES), ("active", "=", True)],
                groupby=["company_id", "program_type"],
            )
        )
        result = {}
        for company, program_type in programs_data:
            result.setdefault(company.id, set()).add(program_type)
        return result

    @api.model
    def _recompute_loyalty_publication(self):
        """Trigger the recomputation of the publication state of the loyalty providers."""
        providers = self.sudo().search([("code", "in", LOYALTY_PAYMENT_CODES)])
        self.env.add_to_compute(self._fields["is_published"], providers)

    # === CRUD METHODS === #

    def copy_data(self, default=None):
        """Override of `payment` to keep loyalty providers in live mode, as they have no test mode."""
        vals_list = super().copy_data(default=default)
        for provider, vals in zip(self, vals_list):
            if provider.code in LOYALTY_PAYMENT_CODES:
                vals["is_live"] = True
        return vals_list

    # === BUSINESS METHODS === #

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        self.ensure_one()
        if self.code not in LOYALTY_PAYMENT_CODES:
            return super()._get_default_payment_method_codes()
        return {self.code}

    @api.model
    def _find_available_providers(
        self,
        company_id,
        partner_id,
        amount,
        *,
        is_express_checkout=False,
        is_validation=False,
        report=None,
        **kwargs,
    ):
        """Override of `payment` to only show the loyalty providers when they can be used.

        Loyalty providers support neither validation operations nor express checkout. The eWallet
        provider is only available to customers having an eWallet with a positive balance.
        """
        providers = super()._find_available_providers(
            company_id,
            partner_id,
            amount,
            is_express_checkout=is_express_checkout,
            is_validation=is_validation,
            report=report,
            **kwargs,
        )
        loyalty_providers = providers.filtered(lambda p: p.code in LOYALTY_PAYMENT_CODES)
        if not loyalty_providers:
            return providers

        unavailable_providers = self.env["payment.provider"]
        if is_validation or is_express_checkout:
            unavailable_providers = loyalty_providers
        else:
            partner = self.env["res.partner"].browse(partner_id).exists()
            for provider in loyalty_providers.filtered(lambda p: p.code == "ewallet"):
                if (
                    not partner
                    or partner.is_public
                    or not self.env["loyalty.card"]._get_payment_cards(
                        "ewallet", partner, provider.company_id
                    )
                ):
                    unavailable_providers |= provider
        return providers - unavailable_providers

    def _get_loyalty_payment_cards_values(self, partner_id, amount, currency):
        """Return the rendering values of the eWallets the partner can pay with.

        Note: `self.ensure_one()`

        :param int partner_id: The partner paying, as a `res.partner` id.
        :param float amount: The amount to pay.
        :param res.currency currency: The currency of the payment.
        :return: The id, code, and usable amount of each eWallet, the highest balance first.
        :rtype: list[dict]
        """
        self.ensure_one()
        partner = self.env["res.partner"].browse(partner_id).exists()
        if self.code != "ewallet" or not partner or partner.is_public:
            return []
        currency = currency or self.company_id.currency_id
        values = []
        for card in self.env["loyalty.card"]._get_payment_cards(
            "ewallet", partner, self.company_id
        ):
            balance = card._get_payment_balance(currency, self.company_id)
            usable_amount = min(balance, currency.round(amount)) if amount else balance
            values.append({
                "id": card.id,
                "code": card.code,
                "name": card.program_id.name,
                "amount": usable_amount,
                "amount_formatted": currency.format(usable_amount),
            })
        return values

    def _get_payment_method_outstanding_account_id(self, payment_method_id):
        """Override of `account_payment` to use the loyalty liability account.

        Paying with a gift card or an eWallet consumes the liability recorded when the card or the
        top-up was sold, instead of debiting an outstanding receipts account.
        """
        if self.code in LOYALTY_PAYMENT_CODES:
            return self.company_id._get_loyalty_liability_account().id
        return super()._get_payment_method_outstanding_account_id(payment_method_id)
