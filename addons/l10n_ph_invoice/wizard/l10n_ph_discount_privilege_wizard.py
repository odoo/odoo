# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command


class L10nPhDiscountPrivilegeWizard(models.TransientModel):
    _name = "l10n_ph.discount.privilege.wizard"
    _description = "Discount Privilege Wizard"
    _check_company_auto = True

    move_id = fields.Many2one("account.move")
    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_l10n_ph_document_company_currency",
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_l10n_ph_document_company_currency",
        readonly=True,
    )
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
    scope_category_ids = fields.Many2many(
        "product.category",
        compute="_compute_scope_category_ids",
    )
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
        "l10n_ph.discount.privilege.wizard.line",
        "wizard_id",
        string="Lines",
    )
    has_applied_privileges = fields.Boolean(compute="_compute_has_applied_privileges")

    def _compute_l10n_ph_document_company_currency(self):
        for wizard in self:
            document = wizard._get_document()
            wizard.company_id = document.company_id or self.env.company
            wizard.currency_id = document.currency_id or self.env.company.currency_id

    @api.depends("line_ids.has_applied_discount_privilege")
    def _compute_has_applied_privileges(self):
        for wizard in self:
            wizard.has_applied_privileges = any(
                line.has_applied_discount_privilege for line in wizard.line_ids
            )

    @api.depends(
        "line_ids.invoice_line_id.product_id",
        "line_ids.invoice_line_id.product_id.categ_id",
    )
    def _compute_available_filters(self):
        for wizard in self:
            products = wizard.line_ids.invoice_line_id.product_id
            wizard.available_product_ids = products
            wizard.available_category_ids = products.categ_id

    @api.depends("category_ids")
    def _compute_scope_category_ids(self):
        for wizard in self:
            categories = wizard.category_ids
            if categories:
                categories |= self.env["product.category"].search(
                    [("id", "child_of", categories.ids)],
                )
            wizard.scope_category_ids = categories

    @api.model
    def _get_document_fields(self):
        """
        Return the names of the (mutually exclusive) fields that can hold
        the document this wizard applies privileges on.

        Concrete modules extend this to add their own document field
        (e.g. order_id in l10n_ph_sale) instead of overriding move_id.
        """
        return ["move_id"]

    def _get_document(self):
        """Return the document (invoice, sale order, ...) set on the wizard."""
        self.ensure_one()
        document_fields = self._get_document_fields()
        for field_name in document_fields:
            document = self[field_name]
            if document:
                return document
        return self[document_fields[0]]

    def _check_document_fields(self, vals):
        """Ensure exactly one of the fields returned by _get_document_fields() is set."""
        document_fields = self._get_document_fields()
        set_fields = [field_name for field_name in document_fields if vals.get(field_name)]
        if not set_fields:
            raise ValidationError(
                self.env._(
                    "You must set one of the following fields to use this wizard: %(fields)s.",
                    fields=", ".join(
                        self._fields[field_name]._description_string(self.env)
                        for field_name in document_fields
                    ),
                ),
            )
        if len(set_fields) > 1:
            raise ValidationError(
                self.env._(
                    "Only one of %(fields)s can be set on the same wizard.",
                    fields=", ".join(
                        self._fields[field_name]._description_string(self.env)
                        for field_name in set_fields
                    ),
                ),
            )

    @api.model_create_multi
    def create(self, vals_list):
        """
        Autopopulate line_ids from the invoice, excluding discount-allocation
        lines (which are handled by other modules and should not receive privileges).
        """
        for vals in vals_list:
            self._check_document_fields(vals)
            if "line_ids" not in vals and vals.get("move_id"):
                move = self.env["account.move"].browse(vals["move_id"])
                invoice_lines = move.invoice_line_ids - move.invoice_line_ids._get_discount_lines()
                vals["line_ids"] = [
                    Command.create({"invoice_line_id": line.id})
                    for line in invoice_lines
                    if line.display_type == "product"
                ]
        return super().create(vals_list)

    def _line_matches_scope(self, source):
        self.ensure_one()
        if self.apply_on == "all":
            return True
        if self.apply_on == "product_category":
            # A privilege granted on a parent category also covers products
            # assigned to any of its child categories.
            return source.product_id.categ_id.id in self.scope_category_ids.ids
        if self.apply_on == "product":
            return bool(self.product_ids) and source.product_id.id in self.product_ids.ids
        return False

    def _privilege_applies_to_line(self, privilege, source):
        """
        Return whether the privilege may be applied to the line.

        An unrestricted privilege applies everywhere; a privilege restricted
        to product categories only applies to lines whose product category
        (or a parent of it) is eligible. A fiscal-position privilege only
        applies to lines whose taxes it actually maps (the VAT it exempts):
        lines with other taxes - e.g. already VAT-exempt or zero-rated -
        are left untouched, as mapping them would drop their taxes without
        any benefit.
        """
        self.ensure_one()
        categories = privilege._l10n_ph_get_applied_category_ids()
        if categories and source.product_id.categ_id.id not in categories.ids:
            return False
        fiscal_position = privilege.fiscal_position_id
        if fiscal_position:
            # Check against the pre-privilege taxes rather than source.tax_ids:
            # once a privilege is applied, tax_ids holds the *mapped* taxes, so
            # checking eligibility for a replacement privilege (or re-checking
            # the preview) must fall back to the original, pre-mapping taxes.
            pre_privilege_taxes = source.l10n_ph_original_tax_ids or source.tax_ids
            if not any(fiscal_position.tax_map.get(str(tax.id)) for tax in pre_privilege_taxes):
                return False
        return True

    def _get_preview_privilege_for_line(self, source):
        self.ensure_one()
        if (
            self.privilege_id
            and self._line_matches_scope(source)
            and self._privilege_applies_to_line(self.privilege_id, source)
        ):
            return self.privilege_id
        return source.l10n_ph_discount_privilege_id

    def _check_can_modify(self):
        self.ensure_one()
        if self.move_id and (
            self.move_id.state != "draft" or not self.move_id.is_sale_document()
        ):
            raise UserError(
                self.env._(
                    "Discount privileges can only be modified on draft customer invoices and credit notes.",
                ),
            )

    def _check_scope_inputs(self):
        self.ensure_one()
        if self.apply_on == "product_category" and not self.category_ids:
            raise UserError(self.env._("Please select at least one product category."))
        if self.apply_on == "product" and not self.product_ids:
            raise UserError(self.env._("Please select at least one product."))

    def action_confirm(self):
        """
        Apply the selected privilege to the invoice.

        Writes the privilege on each matching line, then applies the
        fiscal-position tax mapping, price-unit adaptation, and statutory
        discount in a single write so the FP takes effect without waiting
        for an @api.depends recomputation. Lines marked for removal get their
        privilege restored instead.
        """
        self.ensure_one()
        self._check_can_modify()
        removals = self.line_ids.filtered("remove_discount_privilege")
        if not self.privilege_id and not removals:
            return {"type": "ir.actions.act_window_close"}
        self._check_scope_inputs()

        privilege = self.privilege_id
        applied = False
        for wiz_line in self.line_ids:
            source = wiz_line._get_line_source()
            if not source:
                continue
            if wiz_line.remove_discount_privilege:
                wiz_line._remove_discount_privilege()
                continue
            if (
                not privilege
                or not self._line_matches_scope(source)
                or not self._privilege_applies_to_line(privilege, source)
            ):
                continue
            applied = True
            original_discount = (
                source.l10n_ph_original_discount
                if source.l10n_ph_discount_privilege_id
                else source.discount
            )
            source.l10n_ph_discount_privilege_id = privilege.id
            new_price_unit, original_price_unit = source._adjust_price_unit_from_privilege(
                source.price_unit,
                source.tax_ids,
                source.document_tax_mode,
            )
            new_taxes, original_taxes = source._adjust_taxes_from_privilege(
                source.tax_ids,
            )
            source.write(
                {
                    "price_unit": new_price_unit,
                    "l10n_ph_original_price_unit": original_price_unit,
                    "tax_ids": [Command.set(new_taxes.ids)],
                    "l10n_ph_original_tax_ids": [Command.set(original_taxes.ids)]
                    if original_taxes
                    else [Command.clear()],
                    "discount": privilege.discount_amount * 100.0,
                    "l10n_ph_original_discount": original_discount,
                },
            )
        if privilege and not applied and not removals:
            raise UserError(
                self.env._(
                    "The selected discount privilege does not apply to any line of this document. "
                    "Please check the product categories set on the privilege and the taxes "
                    "applied to the lines.",
                ),
            )
        return {"type": "ir.actions.act_window_close"}

    def action_remove_all(self):
        self.ensure_one()
        self._check_can_modify()
        for wiz_line in self.line_ids:
            wiz_line._remove_discount_privilege()
        return {"type": "ir.actions.act_window_close"}

    @api.onchange("privilege_id")
    def _onchange_privilege_id(self):
        for wizard in self:
            if not wizard.privilege_id:
                continue
            categories = wizard.privilege_id._l10n_ph_get_applied_category_ids()
            if not categories:
                continue
            # On onchange pseudo-records, available_category_ids contains
            # NewId records: intersect with their real counterparts instead.
            available = categories & wizard.available_category_ids._origin
            if available:
                wizard.apply_on = "product_category"
                wizard.category_ids = available


class L10nPhDiscountPrivilegeWizardLine(models.TransientModel):
    _name = "l10n_ph.discount.privilege.wizard.line"
    _description = "Discount Privilege Wizard Line"

    wizard_id = fields.Many2one(
        "l10n_ph.discount.privilege.wizard",
        required=True,
        ondelete="cascade",
    )
    invoice_line_id = fields.Many2one("account.move.line")
    name = fields.Text(
        string="Product",
        compute="_compute_name",
    )
    category_id = fields.Many2one(
        "product.category",
        string="Product Category",
        compute="_compute_category_id",
    )
    currency_id = fields.Many2one(related="wizard_id.currency_id")
    has_discount_privilege = fields.Boolean(
        compute="_compute_preview_fields",
    )
    has_applied_discount_privilege = fields.Boolean(
        compute="_compute_preview_fields",
    )
    remove_discount_privilege = fields.Boolean(
        string="Remove Discount Privilege",
        help="When confirmed, the privilege is removed from the source line "
        "and its original price, taxes and discount are restored.",
    )
    discount = fields.Float(
        string="Discount Applied (%)",
        digits="Discount",
        compute="_compute_preview_fields",
    )
    discount_amount = fields.Monetary(
        string="Discount Amount",
        currency_field="currency_id",
        compute="_compute_preview_fields",
    )

    def _compute_name(self):
        for line in self:
            source = line._get_line_source()
            line.name = source.name

    @api.depends("invoice_line_id.product_id.categ_id")
    def _compute_category_id(self):
        for line in self:
            source = line._get_line_source()
            line.category_id = source.product_id.categ_id if source else False

    # --- Computed preview values ---
    @api.depends(
        "wizard_id.privilege_id",
        "wizard_id.privilege_id.discount_type",
        "wizard_id.privilege_id.discount_amount",
        "wizard_id.apply_on",
        "wizard_id.category_ids",
        "wizard_id.product_ids",
        "remove_discount_privilege",
    )
    def _compute_preview_fields(self):
        for line in self:
            source = line._get_line_source()
            privilege = line.wizard_id._get_preview_privilege_for_line(source)
            if line.remove_discount_privilege:
                privilege = self.env["l10n_ph.discount.privilege"]
            line.has_discount_privilege = bool(privilege)
            line.has_applied_discount_privilege = bool(
                not line.remove_discount_privilege and source.l10n_ph_discount_privilege_id,
            )
            line.discount = privilege.discount_amount * 100.0 if privilege else 0.0
            line.discount_amount = source._l10n_ph_get_preview_discount_amount(
                privilege=privilege,
            )

    def _get_line_source(self):
        self.ensure_one()
        return self.invoice_line_id

    def _remove_discount_privilege(self):
        """
        Clear the privilege on the linked source line and restore the
        original taxes, price unit, and discount in a single write.
        """
        self.ensure_one()
        source = self._get_line_source()
        if not source or not source.l10n_ph_discount_privilege_id:
            return False
        source.write(
            {
                "l10n_ph_discount_privilege_id": False,
                "price_unit": source.l10n_ph_original_price_unit or source.price_unit,
                "l10n_ph_original_price_unit": 0.0,
                "tax_ids": source.l10n_ph_original_tax_ids or source.tax_ids,
                "l10n_ph_original_tax_ids": False,
                "discount": source.l10n_ph_original_discount,
                "l10n_ph_original_discount": 0.0,
            },
        )
        return True

    def action_remove_line_discount(self):
        """
        Mark the line for privilege removal.

        The actual removal is only performed on action_confirm, so cancelling
        the wizard leaves the invoice untouched.
        """
        self.ensure_one()
        self.remove_discount_privilege = True
        return self.wizard_id._get_records_action(
            target="new",
            name=self.env._("Discount Privilege"),
        )
