# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import float_compare


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ph_has_discount_privilege = fields.Boolean(
        compute="_compute_l10n_ph_has_discount_privilege",
    )

    def _prepare_product_base_line_for_taxes_computation(self, product_line):
        result = super()._prepare_product_base_line_for_taxes_computation(product_line)
        if product_line.l10n_ph_discount_privilege_id and product_line.l10n_ph_discount_privilege_previous_tax_ids:
            privilege = product_line.l10n_ph_discount_privilege_id
            if not privilege.tax_id:
                return result
            source_taxes = product_line.l10n_ph_discount_privilege_previous_tax_ids
            tax = privilege.sudo().tax_id
            if tax and tax.amount_type != "group" and tax.amount > 0 and tax._is_price_included(product_line.document_tax_mode):
                # VAT-able privilege (e.g., 5% SC): discount is on total including VAT.
                base = product_line._l10n_ph_get_discount_base_amount(
                    source_taxes, privilege,
                )
                result["price_unit"] = base * (1 - product_line.discount / 100.0)
                result["discount"] = 0.0
            else:
                divisor = product_line._l10n_ph_get_vat_inclusive_divisor(source_taxes)
                if float_compare(divisor, 1.0, precision_rounding=1e-6) != 0:
                    result["price_unit"] = result["price_unit"] / divisor
        return result

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
        wizard = self.env["l10n_ph.discount_privilege.wizard"].create({
            "move_id": self.id,
        })
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Discount Privilege"),
            "res_model": "l10n_ph.discount_privilege.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }
