# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class L10nPhDiscountPrivilegeWizard(models.TransientModel):
    _name = "l10n_ph.discount_privilege.wizard"
    _description = "Discount Privilege Wizard"

    move_id = fields.Many2one("account.move", required=True)
    company_id = fields.Many2one(related="move_id.company_id")
    currency_id = fields.Many2one(related="move_id.currency_id")
    privilege_id = fields.Many2one(
        "l10n_ph.discount.privilege",
        string="Privilege Applied",
        check_company=True,
    )
    apply_on = fields.Selection(
        selection=[
            ("all", "All Order Lines"),
            ("product_category", "Product Categories"),
            ("product", "Products"),
        ],
        string="Apply On",
        default="all",
        required=True,
    )
    product_ids = fields.Many2many(
        "product.product",
        relation="l10n_ph_discount_privilege_wizard_product_rel",
        string="Products",
    )
    category_ids = fields.Many2many("product.category", string="Product Categories")
    available_product_ids = fields.Many2many(
        "product.product",
        relation="l10n_ph_discount_privilege_wizard_available_product_rel",
        compute="_compute_available_filters",
    )
    available_category_ids = fields.Many2many(
        "product.category",
        compute="_compute_available_filters",
    )
    line_ids = fields.One2many(
        "l10n_ph.discount_privilege.wizard.line",
        "wizard_id",
        string="Invoice Lines",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "line_ids" not in vals and vals.get("move_id"):
                move = self.env["account.move"].browse(vals["move_id"])
                vals["line_ids"] = [
                    Command.create({"invoice_line_id": line.id})
                    for line in move.invoice_line_ids
                    if line.display_type == "product"
                ]
        wizards = super().create(vals_list)
        for wizard in wizards:
            wizard._recompute_line_previews()
        return wizards

    def _line_matches_scope(self, invoice_line):
        """Check whether an invoice line is in scope for the current wizard settings."""
        self.ensure_one()
        if self.apply_on == "all":
            return True
        if self.apply_on == "product_category":
            return invoice_line.product_id.categ_id.id in self.category_ids.ids
        if self.apply_on == "product":
            return (
                bool(self.product_ids)
                and invoice_line.product_id.id in self.product_ids.ids
            )
        return False

    def _get_preview_privilege_for_line(self, invoice_line):
        self.ensure_one()
        if self.privilege_id and self._line_matches_scope(invoice_line):
            return self.privilege_id
        return invoice_line.l10n_ph_discount_privilege_id

    def _recompute_line_previews(self):
        """Recompute preview values on all wizard lines based on current scope."""
        self.ensure_one()
        updates = []
        for line in self.line_ids:
            inv = line.invoice_line_id
            privilege = self._get_preview_privilege_for_line(inv)
            vals = {
                "has_discount_privilege": bool(privilege),
                "has_applied_discount_privilege": bool(
                    inv.l10n_ph_discount_privilege_id,
                ),
                "discount": privilege.discount_amount if privilege else 0.0,
            }
            if not privilege:
                vals["discounted_amount"] = 0.0
            elif privilege == inv.l10n_ph_discount_privilege_id:
                vals["discounted_amount"] = inv.l10n_ph_special_discount_amount
            else:
                vals["discounted_amount"] = inv._l10n_ph_get_special_discount_amount(
                    privilege=privilege,
                )
            updates.append(Command.update(line.id, vals))
        self.line_ids = updates

    def _check_can_modify(self, action_label):
        self.ensure_one()
        if not (self.move_id.state == "draft" and self.move_id.is_sale_document()):
            raise UserError(
                self.env._(
                    "Discount privileges can only be %(action)s on draft customer invoices and credit notes.",
                    action=action_label,
                ),
            )

    def _check_scope_inputs(self):
        self.ensure_one()
        if self.apply_on == "product_category" and not self.category_ids:
            raise UserError(self.env._("Please select at least one product category."))
        if self.apply_on == "product" and not self.product_ids:
            raise UserError(self.env._("Please select at least one product."))

    def action_confirm(self):
        self.ensure_one()
        self._check_can_modify("applied")
        if not self.privilege_id:
            return {"type": "ir.actions.act_window_close"}
        if self.privilege_id.company_id != self.company_id:
            raise UserError(
                self.env._("The selected privilege belongs to another company."),
            )
        self._check_scope_inputs()

        privilege = self.privilege_id
        for inv_line in self.line_ids.invoice_line_id:
            if not self._line_matches_scope(inv_line):
                continue
            vals = {
                "l10n_ph_discount_privilege_id": privilege.id,
                "discount": privilege.discount_amount,
            }
            # Save original state only on first application
            if not inv_line.l10n_ph_discount_privilege_id:
                vals["l10n_ph_discount_privilege_previous_tax_ids"] = [
                    Command.set(inv_line.tax_ids.ids),
                ]
                vals["l10n_ph_discount_privilege_previous_discount"] = inv_line.discount
            if privilege.tax_id:
                vals["tax_ids"] = [Command.set(privilege.tax_id.ids)]
            vals["price_unit"] = inv_line.price_unit
            inv_line.write(vals)
        return {"type": "ir.actions.act_window_close"}

    def action_remove_all(self):
        self.ensure_one()
        self._check_can_modify("removed")
        for line in self.move_id.invoice_line_ids:
            if line.display_type == "product":
                line.write(line._l10n_ph_prepare_privilege_removal_vals())
        return {"type": "ir.actions.act_window_close"}

    @api.depends(
        "line_ids.invoice_line_id.product_id",
        "line_ids.invoice_line_id.product_id.categ_id",
    )
    def _compute_available_filters(self):
        for wizard in self:
            products = wizard.line_ids.invoice_line_id.product_id
            wizard.available_product_ids = products
            wizard.available_category_ids = products.categ_id

    @api.onchange("apply_on")
    def _onchange_apply_on(self):
        if self.apply_on != "product":
            self.product_ids = False
        if self.apply_on != "product_category":
            self.category_ids = False
        self._recompute_line_previews()

    @api.onchange("category_ids", "product_ids")
    def _onchange_scope_filters(self):
        """Recompute wizard line previews when scope filters change.

        Many2many-through-Many2one @api.depends paths don't reliably trigger
        onchange recomputation for non-stored fields on transient One2many lines.
        We handle it explicitly here instead.
        """
        self._recompute_line_previews()

    @api.onchange("privilege_id")
    def _onchange_privilege_id(self):
        for wizard in self:
            if not wizard.privilege_id:
                continue
            categories = (
                wizard.privilege_id.applied_to_category_ids
                & wizard.available_category_ids
            )
            if categories:
                wizard.apply_on = "product_category"
                wizard.category_ids = categories
            wizard._recompute_line_previews()


class L10nPhDiscountPrivilegeWizardLine(models.TransientModel):
    _name = "l10n_ph.discount_privilege.wizard.line"
    _description = "Discount Privilege Wizard Line"

    wizard_id = fields.Many2one(
        "l10n_ph.discount_privilege.wizard",
        required=True,
        ondelete="cascade",
    )
    invoice_line_id = fields.Many2one("account.move.line", required=True)
    product_id = fields.Many2one(
        related="invoice_line_id.product_id",
        string="Product Name",
    )
    category_id = fields.Many2one(
        related="invoice_line_id.product_id.categ_id",
        string="Product Category",
    )
    currency_id = fields.Many2one(related="wizard_id.currency_id")
    has_discount_privilege = fields.Boolean()
    has_applied_discount_privilege = fields.Boolean()
    discount = fields.Float(
        string="Discount Applied (%)",
        digits="Discount",
    )
    discounted_amount = fields.Monetary(
        string="Discounted Amount",
        currency_field="currency_id",
    )

    def action_remove_line_discount(self):
        self.ensure_one()
        if not self.invoice_line_id.l10n_ph_discount_privilege_id:
            return False
        self.invoice_line_id.write(
            self.invoice_line_id._l10n_ph_prepare_privilege_removal_vals(),
        )
        self.wizard_id._recompute_line_previews()
        return {
            "type": "ir.actions.act_window",
            "name": "Discount Privilege",
            "res_model": "l10n_ph.discount_privilege.wizard",
            "res_id": self.wizard_id.id,
            "view_mode": "form",
            "target": "new",
        }
