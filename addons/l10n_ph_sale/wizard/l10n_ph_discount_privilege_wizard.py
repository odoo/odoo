# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class L10nPhDiscountPrivilegeWizard(models.TransientModel):
    _inherit = "l10n_ph.discount.privilege.wizard"

    order_id = fields.Many2one("sale.order", string="Sale Order")

    @api.model
    def _get_document_fields(self):
        return [*super()._get_document_fields(), "order_id"]

    @api.model_create_multi
    def create(self, vals_list):
        """
        Autopopulate line_ids from the sale order, excluding non-product
        lines (sections, notes, delivery, down payments and global
        discount lines, which are handled by other features and should
        not receive privileges).
        """
        for vals in vals_list:
            if "line_ids" not in vals and vals.get("order_id"):
                order = self.env["sale.order"].browse(vals["order_id"])
                vals["line_ids"] = [
                    Command.create({"sale_order_line_id": line.id})
                    for line in order.order_line.filtered(
                        lambda line: line._is_product_line()
                    )
                ]
        return super().create(vals_list)

    def _check_can_modify(self):
        super()._check_can_modify()
        if self.order_id and self.order_id.state not in ("draft", "sent"):
            raise UserError(
                self.env._(
                    "Discount privileges can only be modified on draft and sent quotations.",
                ),
            )

    @api.depends(
        "line_ids.sale_order_line_id.product_id",
        "line_ids.sale_order_line_id.product_id.categ_id",
    )
    def _compute_available_filters(self):
        # Extend the base computation (invoice lines) with the products of the
        # sale order lines, instead of re-implementing it.
        super()._compute_available_filters()
        for wizard in self:
            products = wizard.line_ids.sale_order_line_id.product_id
            wizard.available_product_ids += products
            wizard.available_category_ids += products.categ_id


class L10nPhDiscountPrivilegeWizardLine(models.TransientModel):
    _inherit = "l10n_ph.discount.privilege.wizard.line"

    sale_order_line_id = fields.Many2one(
        "sale.order.line",
        string="Sale Order Line",
    )

    @api.depends("sale_order_line_id.product_id.categ_id")
    def _compute_category_id(self):
        super()._compute_category_id()

    def _get_line_source(self):
        self.ensure_one()
        return self.invoice_line_id or self.sale_order_line_id
