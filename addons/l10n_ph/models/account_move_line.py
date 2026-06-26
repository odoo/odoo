# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.tools import float_is_zero, frozendict


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_ph_discount_privilege_id = fields.Many2one(
        "l10n_ph.discount.privilege",
        string="Discount Privilege",
        check_company=True,
        readonly=True,
    )
    l10n_ph_original_tax_ids = fields.Many2many(
        "account.tax",
        relation="account_move_line_l10n_ph_original_tax_rel",
        string="Original Taxes (pre-privilege)",
        readonly=True,
    )
    l10n_ph_discount_privilege_previous_discount = fields.Float(
        string="Previous Discount (pre-privilege)",
        readonly=True,
    )
    l10n_ph_regular_discount_amount = fields.Monetary(
        string="Regular Disc. Amount",
        currency_field="currency_id",
        compute="_compute_l10n_ph_discount_amounts",
        readonly=True,
    )
    l10n_ph_special_discount_amount = fields.Monetary(
        string="Special Disc. Amount",
        currency_field="currency_id",
        compute="_compute_l10n_ph_discount_amounts",
        readonly=True,
    )
    l10n_ph_original_price_unit = fields.Float(
        string="Original Price Unit (pre-divisor)",
        digits="Product Price",
        readonly=True,
    )

    # --- price_unit adjustment when document_tax_mode changes ---

    def _compute_totals(self):
        # Ensure price_unit reflects the current document_tax_mode for
        # FP-privileged lines, so _compute_totals uses the correct base price.
        # Without this, changing document_tax_mode on a privileged invoice
        # would compute subtotal/total from the stale divisor-adjusted price.
        for line in self:
            if (
                line.l10n_ph_discount_privilege_id
                and line.l10n_ph_discount_privilege_id.fiscal_position_id
                and line.l10n_ph_original_tax_ids
            ):
                base_price = line.l10n_ph_original_price_unit or line.price_unit
                divisor = line._l10n_ph_get_privilege_divisor()
                if divisor > 1.0:
                    line.update(
                        {"price_unit": line.currency_id.round(base_price / divisor)},
                    )
                else:
                    line.update({"price_unit": base_price})
        super()._compute_totals()

    # --- Computed taxes with privilege FP ---

    @api.depends("product_id", "l10n_ph_discount_privilege_id")
    def _compute_tax_ids(self):
        ph_privileged = self.filtered(
            lambda line: (
                line.move_id
                and line.move_id.country_code == "PH"
                and line.l10n_ph_discount_privilege_id
            ),
        )
        # Base compute for non-privileged lines first, so the standard
        # product/account tax logic runs before we override.
        super(AccountMoveLine, self - ph_privileged)._compute_tax_ids()
        # Restore originals and clear pre-privilege state on non-privileged PH lines.
        # Undo the price_unit divisor and restore the original tax_ids (which
        # were saved before the privilege FP mapping was applied), so that the
        # line returns to its exact pre-privilege tax configuration even when
        # the product/account defaults differ from the original taxes.
        for line in self - ph_privileged:
            orig_taxes = line.l10n_ph_original_tax_ids
            if orig_taxes:
                divisor = line._l10n_ph_get_vat_inclusive_divisor(
                    orig_taxes,
                    document_tax_mode=line.document_tax_mode,
                )
                if divisor > 1.0:
                    line.price_unit = line.currency_id.round(line.price_unit * divisor)
                line.tax_ids = orig_taxes
                line.update({"l10n_ph_original_tax_ids": False})
                line.l10n_ph_original_price_unit = 0.0
                line.l10n_ph_discount_privilege_previous_discount = 0.0
        # Handle privileged lines: save originals on first FP apply, map through FP,
        # or restore originals for non-FP privileges.
        for line in ph_privileged:
            if (
                line.display_type
                in (
                    "line_section",
                    "line_subsection",
                    "line_note",
                    "payment_term",
                    "cogs",
                )
                or line.is_imported
            ):
                continue
            fpos = line.l10n_ph_discount_privilege_id.sudo().fiscal_position_id
            if fpos:
                # Save original taxes on first privilege application.
                # For wizard-applied privileges, this is a no-op because the
                # wizard already stored l10n_ph_original_tax_ids in the write
                # vals (avoiding recursion from reading tax_ids during compute).
                first_apply = not line.l10n_ph_original_tax_ids
                if first_apply and line.tax_ids:
                    line.update({"l10n_ph_original_tax_ids": line.tax_ids})
                if first_apply:
                    divisor = line._l10n_ph_get_privilege_divisor()
                    if divisor > 1.0:
                        line.update(
                            {
                                "l10n_ph_original_price_unit": line.price_unit,
                                "price_unit": line.currency_id.round(
                                    line.price_unit / divisor,
                                ),
                            },
                        )
                source_taxes = line.l10n_ph_original_tax_ids or line.tax_ids
                if source_taxes:
                    mapped_taxes = line.env["account.tax"]
                    for tax in source_taxes:
                        mapped = fpos.map_tax(tax)
                        mapped_taxes |= mapped or tax
                    line.tax_ids = mapped_taxes
            elif line.l10n_ph_original_tax_ids:
                line.tax_ids = line.l10n_ph_original_tax_ids
                line.update({"l10n_ph_original_tax_ids": False})

    # --- Discount allocation ---

    @api.depends(
        "l10n_ph_discount_privilege_id",
        "l10n_ph_discount_privilege_id.account_id",
        "l10n_ph_discount_privilege_id.fiscal_position_id",
    )
    def _compute_discount_allocation_needed(self):
        super()._compute_discount_allocation_needed()
        for line in self:
            if line.display_type != "product" or not line.l10n_ph_discount_privilege_id:
                continue
            privilege = line.l10n_ph_discount_privilege_id.sudo()
            account = privilege.account_id
            if not account or line.account_id == account:
                line.discount_allocation_needed = False
                continue
            if privilege.fiscal_position_id:
                # price_unit is already adjusted by _compute_price_unit
                base = line.quantity * line.price_unit * line.discount / 100.0
            else:
                base = line._l10n_ph_compute_vat_incl_total() * line.discount / 100.0
            amount_currency = line.currency_id.round(line.move_id.direction_sign * base)
            if not amount_currency:
                line.discount_allocation_needed = False
                continue
            amount = line.company_currency_id.round(
                amount_currency / line.currency_rate,
            )
            line.discount_allocation_needed = [
                (
                    frozendict(
                        {
                            "move_id": line.move_id.id,
                            "account_id": line.account_id.id,
                            "currency_rate": line.currency_rate,
                        },
                    ),
                    frozendict(
                        {
                            "display_type": "discount",
                            "name": _("SC/PWD Discount"),
                            "amount_currency": amount_currency,
                            "balance": amount,
                        },
                    ),
                ),
                (
                    frozendict(
                        {
                            "move_id": line.move_id.id,
                            "account_id": account.id,
                            "currency_rate": line.currency_rate,
                        },
                    ),
                    frozendict(
                        {
                            "display_type": "discount",
                            "name": _("SC/PWD Discount"),
                            "amount_currency": -amount_currency,
                            "balance": -amount,
                        },
                    ),
                ),
            ]

    # --- Discount amounts ---

    @api.depends(
        "quantity",
        "discount",
        "price_unit",
        "product_id.lst_price",
        "tax_ids",
        "move_id.move_type",
        "document_tax_mode",
        "l10n_ph_discount_privilege_id",
        "l10n_ph_discount_privilege_id.discount_amount",
        "l10n_ph_discount_privilege_id.fiscal_position_id",
    )
    def _compute_l10n_ph_discount_amounts(self):
        for line in self:
            if line.display_type != "product" or not line.move_id.is_sale_document():
                line.l10n_ph_regular_discount_amount = 0.0
                line.l10n_ph_special_discount_amount = 0.0
                continue

            if line.l10n_ph_discount_privilege_id:
                privilege = line.l10n_ph_discount_privilege_id.sudo()
                if privilege.fiscal_position_id:
                    line.l10n_ph_special_discount_amount = (
                        line.price_unit * line.quantity * line.discount / 100.0
                    )
                else:
                    total_vat_incl = line._l10n_ph_compute_vat_incl_total()
                    line.l10n_ph_special_discount_amount = (
                        total_vat_incl * line.discount / 100.0
                    )
                line.l10n_ph_regular_discount_amount = 0.0
            else:
                line.l10n_ph_special_discount_amount = 0.0
                line.l10n_ph_regular_discount_amount = (
                    line._l10n_ph_compute_regular_discount_amount()
                )

    def _l10n_ph_compute_regular_discount_amount(self):
        self.ensure_one()
        source_taxes = self.tax_ids
        divisor = self._l10n_ph_get_vat_inclusive_divisor(source_taxes)
        if self.discount:
            return (self.price_unit * self.quantity * self.discount / 100.0) / divisor
        reference_price = self._l10n_ph_get_discount_reference_unit_price()
        if reference_price > self.price_unit:
            return (self.quantity * (reference_price - self.price_unit)) / divisor
        return 0.0

    def _l10n_ph_get_privilege_divisor(self):
        self.ensure_one()
        privilege = self.l10n_ph_discount_privilege_id
        if not privilege or not privilege.fiscal_position_id:
            return 1.0
        # Ensure _compute_tax_ids has populated l10n_ph_original_tax_ids
        # before we decide which taxes to use for the divisor.
        # Reading self.tax_ids triggers _compute_tax_ids (which depends on
        # it) so that the first_apply block stores the original taxes before
        # FP mapping. Without this, we might read already-mapped taxes and
        # compute a wrong divisor for newly-created FP-based privileged lines.
        if not self.l10n_ph_original_tax_ids:
            self.tax_ids
        source_taxes = self.l10n_ph_original_tax_ids or self.tax_ids
        return self._l10n_ph_get_vat_inclusive_divisor(
            source_taxes,
            document_tax_mode=self.document_tax_mode,
        )

    def _l10n_ph_get_vat_inclusive_divisor(self, taxes, document_tax_mode=None):
        self.ensure_one()
        included_taxes = taxes.flatten_taxes_hierarchy().filtered(
            lambda t: (
                t.amount > 0
                and t.amount_type in ("percent", "division")
                and t._is_price_included(document_tax_mode)
            ),
        )
        if included_taxes:
            return 1.0 + sum(included_taxes.mapped("amount")) / 100.0
        return 1.0

    def _l10n_ph_get_discount_reference_unit_price(self):
        self.ensure_one()
        if "sale_line_ids" in self._fields and self.sale_line_ids:
            sale_line = self.sale_line_ids[:1]
            reference_price = sale_line.price_unit
            if (
                not sale_line.discount
                and sale_line.pricelist_item_id
                and not sale_line.pricelist_item_id._show_discount()
            ):
                base_price = sale_line._get_pricelist_price_before_discount()
                if not float_is_zero(
                    base_price,
                    precision_rounding=sale_line.currency_id.rounding,
                ):
                    reference_price = base_price
            return reference_price
        if self.product_id:
            return self.product_id.lst_price
        return self.price_unit

    # --- Preview helper for wizard ---

    def _l10n_ph_compute_vat_incl_total(self):
        total = self.price_unit * self.quantity
        divisor = self._l10n_ph_get_vat_inclusive_divisor(
            self.tax_ids,
            document_tax_mode=self.document_tax_mode,
        )
        if divisor > 1.0:
            return total
        for tax in self.tax_ids.flatten_taxes_hierarchy():
            if (
                tax.amount > 0
                and tax.amount_type in ("percent", "division")
                and not tax._is_price_included(self.document_tax_mode)
            ):
                total *= 1.0 + tax.amount / 100.0
        return total

    def _l10n_ph_get_preview_discount_amount(self, privilege):
        self.ensure_one()
        if not privilege:
            return 0.0
        if privilege == self.l10n_ph_discount_privilege_id:
            return self.l10n_ph_special_discount_amount
        if privilege.fiscal_position_id:
            # Preview needs to account for the divisor adjustment that the
            # wizard's action_confirm will apply to price_unit.
            divisor = self._l10n_ph_get_vat_inclusive_divisor(
                self.tax_ids,
                document_tax_mode=self.document_tax_mode,
            )
            base_price = (
                self.currency_id.round(self.price_unit / divisor)
                if divisor > 1.0
                else self.price_unit
            )
            return base_price * self.quantity * privilege.discount_amount / 100.0
        return (
            self._l10n_ph_compute_vat_incl_total() * privilege.discount_amount / 100.0
        )
