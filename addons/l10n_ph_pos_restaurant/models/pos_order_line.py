# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Command


class PosOrderLine(models.Model):
    _inherit = ["pos.order.line", "l10n_ph.discount.privilege.line.mixin"]
    _name = "pos.order.line"

    l10n_ph_original_tax_ids = fields.Many2many(
        relation="pos_order_line_l10n_ph_original_tax_rel",
    )
    l10n_ph_discount_privilege_holder_id = fields.Many2one(
        "l10n_ph.pos.discount.privilege.holder",
        string="SC/PWD ID Holder",
        ondelete="restrict",
        index="btree_not_null",
    )

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            *super()._load_pos_data_fields(config),
            "l10n_ph_discount_privilege_id",
            "l10n_ph_original_tax_ids",
            "l10n_ph_original_price_unit",
            "l10n_ph_original_discount",
            "l10n_ph_discount_privilege_holder_id",
        ]

    # --- Model-specific hooks for the mixin ---

    def _l10n_ph_skip_discount_amounts(self):
        self.ensure_one()
        return self.product_id.type == "combo"

    def _l10n_ph_prepare_taxed_base_line(self, discount=None):
        """
        Build a fully tax-computed base line for this order line, the way
        _prepare_account_move_line_data_from_base_line does for invoicing.

        :param discount: when set, overrides the line's own discount (e.g.
            0.0 to get the pre-discount/gross tax details) before the tax
            engine computes tax_details on it.
        """
        self.ensure_one()
        company = self.company_id or self.env.company
        base_line = self._prepare_base_lines_for_taxes_computation()[0]
        if discount is not None:
            base_line["discount"] = discount
        self.env["account.tax"]._add_tax_details_in_base_line(base_line, company)
        self.env["account.tax"]._round_base_lines_tax_details([base_line], company)
        return base_line

    def _l10n_ph_get_discount_price_details(self):
        """
        Return the gross (pre-discount) price amounts and the discount
        amounts derived from the current POS order line.

        The gross amounts are recomputed with the tax engine on a base line
        without discount: price_subtotal/price_subtotal_incl are pre-rounded
        amounts that would introduce inaccuracies (and are zero at 100%
        discount).
        """
        self.ensure_one()
        base_line = self._l10n_ph_prepare_taxed_base_line(discount=0.0)
        gross_price_subtotal = base_line["tax_details"]["raw_total_excluded_currency"]
        gross_price_total = base_line["tax_details"]["raw_total_included_currency"]
        return (
            gross_price_subtotal,
            gross_price_subtotal - self.price_subtotal,
            gross_price_total,
            gross_price_total - self.price_subtotal_incl,
        )

    @api.depends(
        "price_unit",
        "qty",
        "discount",
        "tax_ids",
        "l10n_ph_discount_privilege_id",
    )
    def _compute_l10n_ph_discount_amounts(self):
        super()._compute_l10n_ph_discount_amounts()

    # --- Splitting engine helpers (called from pos.order) ---

    def _l10n_ph_refresh_amounts(self):
        """
        Refresh price_subtotal(_incl) and extra_tax_data from the current
        price_unit/discount/qty/tax_ids: unlike account.move.line/
        sale.order.line, POS does not auto-compute these from their
        dependencies, and extra_tax_data is normally only ever computed
        client-side, so any server-side mutation must refresh it too or the
        POS frontend's tax display crashes on stale/mismatched data.
        """
        self.ensure_one()
        base_line = self._l10n_ph_prepare_taxed_base_line()
        vals = self._compute_amount_line_all()
        vals["extra_tax_data"] = self.env["account.tax"]._export_base_line_extra_tax_data(base_line)
        self.write(vals)

    def _l10n_ph_set_qty(self, qty):
        """Resize a (regular, unprivileged) share of a split line."""
        self.ensure_one()
        self.qty = qty
        self._l10n_ph_refresh_amounts()

    def _l10n_ph_apply_holder_privilege(self, holder, qty):
        """
        Attribute this line to ``holder``: set its quantity, apply the
        holder's discount privilege (VAT-exempt tax swap + statutory
        discount) via the mixin, and refresh the stored subtotals.
        """
        self.ensure_one()
        self.qty = qty
        self.l10n_ph_discount_privilege_id = holder.privilege_id.id
        self.l10n_ph_discount_privilege_holder_id = holder.id
        new_price_unit, original_price_unit = self._adjust_price_unit_from_privilege(
            self.price_unit, self.tax_ids, "tax_excluded",
        )
        new_taxes, original_taxes = self._adjust_taxes_from_privilege(self.tax_ids)
        self.write(
            {
                "price_unit": new_price_unit,
                "l10n_ph_original_price_unit": original_price_unit,
                "tax_ids": [Command.set(new_taxes.ids)],
                "l10n_ph_original_tax_ids": [Command.set(original_taxes.ids)] if original_taxes else False,
                # A line entering this method is never already privileged (the
                # engine only calls it on fresh/copied shares), so the current
                # discount is always the pre-privilege one worth preserving —
                # mirrors L10nPhDiscountPrivilegeWizard.action_confirm.
                "l10n_ph_original_discount": self.discount,
                "discount": holder.privilege_id.discount_amount * 100.0,
            },
        )
        self._l10n_ph_refresh_amounts()
