# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models
from odoo.fields import Command
from odoo.tools import float_is_zero, frozendict


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_ph_discount_privilege_id = fields.Many2one(
        "l10n_ph.discount.privilege",
        string="Discount Privilege",
        check_company=True,
        readonly=True,
    )
    l10n_ph_discount_privilege_previous_tax_ids = fields.Many2many(
        "account.tax",
        relation="account_move_line_l10n_ph_prev_tax_rel",
        column1="move_line_id",
        column2="tax_id",
        string="Discount Privilege Previous Taxes",
        readonly=True,
    )
    l10n_ph_discount_privilege_previous_discount = fields.Float(
        string="Discount Privilege Previous Discount (%)",
        digits="Discount",
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

    # --- Helpers for privilege application/removal ---

    def _l10n_ph_get_source_taxes_and_price_unit(self):
        self.ensure_one()
        if self.l10n_ph_discount_privilege_previous_tax_ids:
            return self.l10n_ph_discount_privilege_previous_tax_ids, self.price_unit
        return self.tax_ids, self.price_unit

    def _l10n_ph_prepare_privilege_removal_vals(self):
        self.ensure_one()
        vals = {
            "l10n_ph_discount_privilege_id": False,
            "discount": self.l10n_ph_discount_privilege_previous_discount,
            "l10n_ph_discount_privilege_previous_discount": 0.0,
            "l10n_ph_discount_privilege_previous_tax_ids": [Command.clear()],
        }
        if self.l10n_ph_discount_privilege_previous_tax_ids:
            vals["tax_ids"] = [
                Command.set(self.l10n_ph_discount_privilege_previous_tax_ids.ids),
            ]
        return vals

    def _l10n_ph_get_vat_inclusive_divisor(self, taxes):
        self.ensure_one()
        included_taxes = taxes.flatten_taxes_hierarchy().filtered(
            lambda t: (
                t.amount > 0
                and t.amount_type in ("percent", "division")
                and t._is_price_included(self.document_tax_mode)
            ),
        )
        if included_taxes:
            return 1.0 + sum(included_taxes.mapped("amount")) / 100.0
        return 1.0

    def _l10n_ph_get_discount_base_amount(self, source_taxes, privilege=None):
        """Get the base amount on which the special discount percentage is applied.

        For VAT-exempt privileges (20% SC/PWD with group/0% tax), the base is the
        price_unit adjusted for VAT-inclusive source taxes (i.e., the VAT-exclusive amount).

        For VAT-able privileges (5% SC with positive-rate price_include tax), the base
        is the total amount including VAT from the source taxes.
        """
        self.ensure_one()
        tax = privilege.sudo().tax_id if privilege else None
        if tax and tax.amount_type != "group" and tax.amount > 0 and tax._is_price_included(self.document_tax_mode):
            # VAT-able privilege: base is total including VAT
            base = self.price_unit * self.quantity
            for src_tax in source_taxes.flatten_taxes_hierarchy():
                if src_tax.amount > 0 and src_tax.amount_type == "percent" and not src_tax._is_price_included(self.document_tax_mode):
                    base *= (1 + src_tax.amount / 100)
            return base
        divisor = self._l10n_ph_get_vat_inclusive_divisor(source_taxes)
        return self.price_unit * self.quantity / divisor

    def _l10n_ph_get_special_discount_amount(self, privilege=None):
        self.ensure_one()
        privilege = privilege or self.l10n_ph_discount_privilege_id
        if not privilege:
            return 0.0
        source_taxes, _ = self._l10n_ph_get_source_taxes_and_price_unit()
        base = self._l10n_ph_get_discount_base_amount(source_taxes, privilege)
        return base * (privilege.sudo().discount_amount / 100.0)

    # --- Computed fields ---

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
        "l10n_ph_discount_privilege_previous_tax_ids",
    )
    def _compute_l10n_ph_discount_amounts(self):
        for line in self:
            if line.display_type != "product" or not line.move_id.is_sale_document():
                line.l10n_ph_regular_discount_amount = 0.0
                line.l10n_ph_special_discount_amount = 0.0
                continue

            line.l10n_ph_special_discount_amount = (
                line._l10n_ph_get_special_discount_amount()
            )

            if line.l10n_ph_discount_privilege_id:
                line.l10n_ph_regular_discount_amount = 0.0
                continue

            line.l10n_ph_regular_discount_amount = (
                line._l10n_ph_compute_regular_discount_amount()
            )

    def _l10n_ph_compute_regular_discount_amount(self):
        self.ensure_one()
        source_taxes, _ = self._l10n_ph_get_source_taxes_and_price_unit()
        divisor = self._l10n_ph_get_vat_inclusive_divisor(source_taxes)
        if self.discount:
            return (self.price_unit * self.quantity * self.discount / 100.0) / divisor
        reference_price = self._l10n_ph_get_discount_reference_unit_price()
        if reference_price > self.price_unit:
            return (self.quantity * (reference_price - self.price_unit)) / divisor
        return 0.0

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

    # --- Discount allocation override ---

    @api.depends(
        "account_id",
        "company_id",
        "discount",
        "price_unit",
        "quantity",
        "currency_rate",
        "analytic_distribution",
        "document_tax_mode",
        "l10n_ph_discount_privilege_id",
        "l10n_ph_discount_privilege_id.account_id",
    )
    def _compute_discount_allocation_needed(self):
        super()._compute_discount_allocation_needed()

        privileged_lines = self.move_id.line_ids.filtered(
            lambda line_item: (
                line_item.display_type == "product"
                and line_item.l10n_ph_discount_privilege_id
            ),
        )
        if not privileged_lines:
            return

        # Re-compute discount allocation for privileged lines using the privilege's account.
        # price_unit is always the original user-entered price (never mutated by privilege).
        line2discounted_amount = {}
        for line in privileged_lines:
            privilege_account = line.l10n_ph_discount_privilege_id.account_id
            source_taxes = (
                line.l10n_ph_discount_privilege_previous_tax_ids
                or line.tax_ids
            )
            base = line._l10n_ph_get_discount_base_amount(
                source_taxes, line.l10n_ph_discount_privilege_id,
            )
            amount_currency = line.currency_id.round(
                line.move_id.direction_sign * base * line.discount / 100,
            )
            if not amount_currency or line.account_id == privilege_account:
                continue
            amount = line.company_currency_id.round(
                amount_currency / line.currency_rate,
            )
            line2discounted_amount[line] = [
                (line.account_id, amount_currency, amount),
                (privilege_account, -amount_currency, -amount),
            ]

        distribution_totals = defaultdict(lambda: defaultdict(float))
        for line, discounted_amounts in line2discounted_amount.items():
            for account, _amount_currency, amount in discounted_amounts:
                key = frozendict(
                    {
                        "move_id": line.move_id.id,
                        "account_id": account.id,
                        "currency_rate": line.currency_rate,
                    },
                )
                for analytic_account_id in line.analytic_distribution or {}:
                    distribution_totals[key][analytic_account_id] += amount

        for line in self.filtered("l10n_ph_discount_privilege_id"):
            if line not in line2discounted_amount:
                line.discount_allocation_needed = False
                continue

            discount_allocation_needed = {}
            for account, amount_currency, amount in line2discounted_amount[line]:
                key = frozendict(
                    {
                        "move_id": line.move_id.id,
                        "account_id": account.id,
                        "currency_rate": line.currency_rate,
                    },
                )
                dist = distribution_totals[key]
                total = sum(dist.values()) or 1
                key_needed = (
                    frozendict(
                        {
                            "move_id": line.move_id._origin.id,
                            "account_id": account._origin.id,
                            "currency_rate": line.currency_rate,
                        },
                    )
                    if not line.move_id.id
                    else key
                )
                discount_allocation_needed[key_needed] = frozendict(
                    {
                        "display_type": "discount",
                        "name": self.env._("Discount"),
                        "amount_currency": amount_currency,
                        "balance": amount,
                        "analytic_distribution": {
                            acct_id: 100 * value / total
                            for acct_id, value in dist.items()
                        },
                    },
                )
            line.discount_allocation_needed = list(discount_allocation_needed.items())
