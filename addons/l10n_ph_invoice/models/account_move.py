# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ph_has_discount_privilege = fields.Boolean(
        compute="_compute_l10n_ph_has_discount_privilege",
    )

    @api.depends("invoice_line_ids.l10n_ph_discount_privilege_id", "move_type")
    def _compute_l10n_ph_has_discount_privilege(self):
        for move in self:
            move.l10n_ph_has_discount_privilege = move.is_sale_document() and any(
                line.l10n_ph_discount_privilege_id
                for line in move.invoice_line_ids
                if line.display_type == "product"
            )

    def action_open_discount_privilege_wizard(self):
        self.ensure_one()
        wizard = self.env["l10n_ph.discount.privilege.wizard"].create(
            {"move_id": self.id},
        )
        return wizard._get_records_action(
            target="new",
            name=self.env._("Discount Privilege"),
        )

    def _l10n_ph_cas_get_invoice_report_values(self):
        """
        Add the privilege discount breakdown: the BIR invoice shows the
        privilege discount as a separate total line.

        The discount is the tax-excluded one when the invoice shows VAT, as it
        is deducted from the amount net of VAT; otherwise it is deducted from
        the total sales and is thus tax-included.

        The sales breakdown is shown before the discount as well, except for
        the VATable sales: the VAT shown next to them is computed on the
        discounted amount, which must thus remain the VATable sales. The
        breakdown then falls short of the amount net of VAT by the discount
        granted on VATable sales, e.g. the special discounts keeping the VAT.
        """
        vals = super()._l10n_ph_cas_get_invoice_report_values()
        base_keys = {
            group_id: f"{key}_base"
            for key, group_id in self._l10n_ph_cas_get_tax_groups().items()
            if group_id and key != "vatable"
        }
        privilege_lines = self.invoice_line_ids.filtered(
            lambda line: line.display_type == "product" and line.l10n_ph_discount_privilege_id,
        )
        discount_excluded = discount_included = 0.0
        for line in privilege_lines:
            gross_price_subtotal, _, gross_price_total, _ = line._l10n_ph_get_discount_price_details()
            line_discount = self.currency_id.round(gross_price_subtotal) - line.price_subtotal
            discount_excluded += line_discount
            discount_included += self.currency_id.round(gross_price_total) - line.price_total
            for group in line.tax_ids.flatten_taxes_hierarchy().tax_group_id:
                if group.id in base_keys:
                    vals[base_keys[group.id]] += line_discount

        privilege_labels = {"sc": "SC", "pwd": "PWD"}
        vals["privilege_label"] = "/".join(dict.fromkeys(
            # No short label exists for special discounts: use the privilege name
            privilege_labels.get(privilege.discount_type, privilege.name)
            for privilege in privilege_lines.l10n_ph_discount_privilege_id
        ))
        vals["privilege_discount"] = self.currency_id.round(
            discount_excluded if vals["has_vat"] else discount_included,
        )
        return vals
