# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import frozendict


class AccountMoveLine(models.Model):
    _inherit = ["account.move.line", "l10n_ph.discount.privilege.line.mixin"]
    _name = "account.move.line"

    l10n_ph_original_tax_ids = fields.Many2many(
        relation="account_move_line_l10n_ph_original_tax_rel",
    )

    # --- Model-specific hooks for the mixin ---

    def _l10n_ph_skip_discount_amounts(self):
        self.ensure_one()
        return self.display_type != "product" or not self.move_id.is_sale_document()

    def _l10n_ph_get_discount_price_details(self):
        """
        Return the gross (pre-discount) price amounts and the discount
        amounts derived from the current AML.

        The gross amounts are recomputed with the tax engine on a base line
        without discount: price_subtotal/price_total are pre-rounded amounts
        that would introduce inaccuracies (and are zero at 100% discount).
        """
        self.ensure_one()
        company = self.company_id or self.env.company
        base_line = self.move_id._prepare_product_base_line_for_taxes_computation(self)
        base_line["discount"] = 0.0
        self.env["account.tax"]._add_tax_details_in_base_line(base_line, company)
        self.env["account.tax"]._round_base_lines_tax_details([base_line], company)
        gross_price_subtotal = base_line["tax_details"]["raw_total_excluded_currency"]
        gross_price_total = base_line["tax_details"]["raw_total_included_currency"]
        return (
            gross_price_subtotal,
            gross_price_subtotal - self.price_subtotal,
            gross_price_total,
            gross_price_total - self.price_total,
        )

    @api.depends(
        "price_unit",
        "quantity",
        "discount",
        "tax_ids",
        "document_tax_mode",
        "l10n_ph_discount_privilege_id",
    )
    def _compute_l10n_ph_discount_amounts(self):
        super()._compute_l10n_ph_discount_amounts()

    # --- Discount allocation (invoice lines only) ---

    @api.depends(
        "account_id",
        "company_id",
        "discount",
        "price_unit",
        "quantity",
        "currency_rate",
        "analytic_distribution",
        "l10n_ph_discount_privilege_id",
        "l10n_ph_special_discount_amount",
    )
    def _compute_discount_allocation_needed(self):
        """
        Override allocation for privileged lines.

        The mixin already computes l10n_ph_special_discount_amount on the
        correct base for the privilege type ("special" uses the VAT-inclusive
        gross total, SC/PWD the VAT-exclusive gross subtotal), so we simply
        allocate that amount to the privilege's account. super() handles the
        non-privileged lines; privileged lines are then re-routed to the
        privilege account, since the base computation would allocate their
        discount on the move's default discount allocation account (or drop
        it altogether when the company has none).
        """
        super()._compute_discount_allocation_needed()
        for move in self.move_id:
            # The base computation covers every line of the move, even ones
            # not in `self` (e.g. a sibling line whose privilege is being
            # removed): re-route all privileged lines to their target account.
            for line in move.line_ids.filtered("l10n_ph_discount_privilege_id"):
                priv = line.l10n_ph_discount_privilege_id
                if not priv.account_id:
                    line.discount_allocation_needed = False
                    line.discount_allocation_dirty = True
                    continue
                amount_currency = line.currency_id.round(
                    line.move_id.direction_sign * line.l10n_ph_special_discount_amount,
                )
                amount = line.company_currency_id.round(amount_currency / line.currency_rate)
                base_key = {
                    "move_id": line.move_id._origin.id,
                    "currency_rate": line.currency_rate,
                }
                line.discount_allocation_needed = [
                    (
                        frozendict(account_id=line.account_id._origin.id, **base_key),
                        frozendict(
                            display_type="discount",
                            name=self.env._("Discount"),
                            amount_currency=amount_currency,
                            balance=amount,
                            analytic_distribution={},
                        ),
                    ),
                    (
                        frozendict(account_id=priv.account_id._origin.id, **base_key),
                        frozendict(
                            display_type="discount",
                            name=self.env._("Discount"),
                            amount_currency=-amount_currency,
                            balance=-amount,
                            analytic_distribution={},
                        ),
                    ),
                ]
                line.discount_allocation_dirty = True
