# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Command


class SaleOrderLine(models.Model):
    _inherit = ["sale.order.line", "l10n_ph.discount.privilege.line.mixin"]
    _name = "sale.order.line"

    l10n_ph_original_tax_ids = fields.Many2many(
        relation="sale_order_line_l10n_ph_original_tax_rel",
    )

    # --- Model-specific hooks for the mixin ---

    def _l10n_ph_skip_discount_amounts(self):
        self.ensure_one()
        return bool(self.display_type)

    def _l10n_ph_get_discount_price_details(self):
        """
        Return the gross (pre-discount) price amounts and the discount
        amounts derived from the current SOL.

        The gross amounts are recomputed with the tax engine on a base line
        without discount: price_subtotal/price_total are pre-rounded amounts
        that would introduce inaccuracies (and are zero at 100% discount).
        """
        self.ensure_one()
        company = self.company_id or self.env.company
        base_line = self._prepare_base_line_for_taxes_computation(discount=0.0)
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
        "product_uom_qty",
        "discount",
        "tax_ids",
        "document_tax_mode",
        "l10n_ph_discount_privilege_id",
    )
    def _compute_l10n_ph_discount_amounts(self):
        super()._compute_l10n_ph_discount_amounts()

    # --- Invoice preparation ---

    def _prepare_invoice_line(self, **optional_values):
        # Propagate the privilege and its original values to the invoice line,
        # so it behaves exactly like a line the privilege was applied on.
        res = super()._prepare_invoice_line(**optional_values)
        if self.l10n_ph_discount_privilege_id:
            res.update(
                {
                    "l10n_ph_discount_privilege_id": self.l10n_ph_discount_privilege_id.id,
                    "l10n_ph_original_tax_ids": [Command.set(self.l10n_ph_original_tax_ids.ids)],
                    "l10n_ph_original_price_unit": self.l10n_ph_original_price_unit,
                    "l10n_ph_original_discount": self.l10n_ph_original_discount,
                },
            )
        return res
