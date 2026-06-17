# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.l10n_ph.tests.common import TestPhCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestDiscountPrivilegeWizard(TestPhCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        discount_group = cls.env.ref("l10n_ph.group_l10n_ph_discount_privilege")
        cls.env.user.write({"group_ids": [Command.link(discount_group.id)]})
        cls.base_tax = cls._create_tax("12% VAT", 12)
        cls.tax_incl = cls._create_tax(
            "12% VAT INCL",
            12,
            amount_type="division",
            price_include=True,
        )
        cls.privilege_tax = cls._create_tax("VAT Exempt", 0)
        cls.special_discount_account = cls.company_data["default_account_revenue"].copy(
            {
                "name": "Discount Privilege Account",
            },
        )
        cls.privilege = (
            cls.env["l10n_ph.discount.privilege"]
            .sudo()
            .create(
                {
                    "name": "Senior Citizen",
                    "discount_amount": 20.0,
                    "tax_id": cls.privilege_tax.id,
                    "account_id": cls.special_discount_account.id,
                },
            )
        )
        cls.privilege_without_tax = (
            cls.env["l10n_ph.discount.privilege"]
            .sudo()
            .create(
                {
                    "name": "Senior Citizen VAT EXCL",
                    "discount_amount": 20.0,
                    "account_id": cls.special_discount_account.id,
                },
            )
        )
        cls.privilege_with_categories = (
            cls.env["l10n_ph.discount.privilege"]
            .sudo()
            .create(
                {
                    "name": "PWD Category Scoped",
                    "discount_amount": 20.0,
                    "tax_id": cls.privilege_tax.id,
                    "account_id": cls.special_discount_account.id,
                    "applied_to_category_ids": [Command.set([])],
                },
            )
        )

        cls.category_a = cls.env["product.category"].create({"name": "Category A"})
        cls.category_b = cls.env["product.category"].create({"name": "Category B"})
        cls.product_a = cls.env["product.product"].create(
            {
                "name": "Product A",
                "categ_id": cls.category_a.id,
                "list_price": 120.0,
            },
        )
        cls.product_b = cls.env["product.product"].create(
            {
                "name": "Product B",
                "categ_id": cls.category_b.id,
                "list_price": 220.0,
            },
        )
        cls.privilege_with_categories.write(
            {"applied_to_category_ids": [Command.set(cls.category_a.ids)]},
        )

    def _line_vals(
        self,
        *,
        name="Line",
        product=None,
        quantity=1.0,
        price_unit=100.0,
        tax=None,
        discount=0.0,
        **extra,
    ):
        vals = {
            "name": name,
            "product_id": (product or self.product_a).id,
            "account_id": self.company_data["default_account_revenue"].id,
            "quantity": quantity,
            "price_unit": price_unit,
        }
        if tax is None:
            tax = self.base_tax
        if tax:
            vals["tax_ids"] = [Command.set(tax.ids)]
        if discount:
            vals["discount"] = discount
        vals.update(extra)
        return vals

    def _create_invoice(self, *line_vals):
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [Command.create(vals) for vals in line_vals],
            },
        )

    def _create_wizard(self, invoice, **vals):
        return (
            self.env["l10n_ph.discount_privilege.wizard"]
            .with_context(default_move_id=invoice.id)
            .create(vals)
        )

    def _assert_discount_allocation(self, invoice, line, amount):
        self.assertRecordValues(
            invoice.line_ids.filtered(
                lambda line_item: line_item.display_type == "discount",
            ).sorted(
                "amount_currency",
            ),
            [
                {
                    "account_id": line.account_id.id,
                    "amount_currency": -amount,
                },
                {
                    "account_id": self.special_discount_account.id,
                    "amount_currency": amount,
                },
            ],
        )

    def test_apply_sets_privilege_tax(self):
        """Applying a SC/PWD privilege to a product-category scope replaces VAT with the
        privilege's VAT-exempt tax on matching lines only, and creates the corresponding
        discount-allocation journal entries."""
        invoice = self._create_invoice(
            self._line_vals(name="Line A", product=self.product_a, price_unit=100.0),
            self._line_vals(name="Line B", product=self.product_b, price_unit=200.0),
        )

        wizard = self._create_wizard(
            invoice,
            privilege_id=self.privilege.id,
            apply_on="product_category",
            category_ids=[Command.set(self.category_a.ids)],
        )
        wizard.action_confirm()

        # line_a matches Category A → privilege applied; line_b does not → unchanged
        line_a, line_b = invoice.invoice_line_ids.sorted("sequence")
        self.assertEqual(line_a.discount, 20.0)
        self.assertEqual(line_a.tax_ids, self.privilege.tax_id)
        self.assertTrue(line_a.l10n_ph_discount_privilege_id)
        self.assertEqual(line_a.l10n_ph_discount_privilege_id, self.privilege)
        self.assertAlmostEqual(line_a.price_subtotal, 80.0)
        self.assertAlmostEqual(line_a.price_total, 80.0)
        self.assertAlmostEqual(line_a.l10n_ph_special_discount_amount, 20.0)
        self.assertEqual(line_b.discount, 0.0)
        self.assertEqual(line_b.tax_ids, self.base_tax)
        self.assertAlmostEqual(invoice.amount_total, 304.0)
        # Two discount-allocation lines: debit revenue, credit privilege discount account
        self._assert_discount_allocation(invoice, line_a, 20.0)

    def test_open_wizard_action_returns_correct_action(self):
        """Opening the SC/PWD wizard from an invoice returns an action with the
        correct context so that the wizard is pre-populated with the invoice data."""
        invoice = self._create_invoice(
            self._line_vals(name="Line A", product=self.product_a, price_unit=100.0),
        )

        action = invoice.action_open_discount_privilege_wizard()
        self.assertEqual(action["res_model"], "l10n_ph.discount_privilege.wizard")
        self.assertEqual(action["context"]["default_move_id"], invoice.id)

        # Creating the wizard via the action's context produces a valid wizard
        wizard = self._create_wizard(invoice)
        self.assertEqual(wizard.move_id, invoice)
        self.assertEqual(wizard.line_ids.invoice_line_id, invoice.invoice_line_ids)

    def test_discount_privilege_records_are_hidden_outside_ph_company(self):
        """A Discount Privilege record should not be accessible when the active company
        is not a Philippine company."""
        other_company = self.env["res.company"].create(
            {
                "name": "Non-PH Company",
                "country_id": self.env.ref("base.us").id,
            },
        )
        privilege = self.env["l10n_ph.discount.privilege"].sudo().create(
            {
                "name": "PH Only",
                "discount_amount": 10.0,
                "account_id": self.special_discount_account.id,
            },
        )

        self.assertTrue(self.env["l10n_ph.discount.privilege"].search([("id", "=", privilege.id)]))
        self.assertFalse(
            self.env["l10n_ph.discount.privilege"].with_company(other_company).search(
                [("id", "=", privilege.id)],
            ),
        )

    def test_invoicing_user_can_apply_but_not_configure_privileges(self):
        """An invoicing user should be able to open the wizard but not create or manage
        discount privilege master data from the search dialog."""
        invoice_user = self.env["res.users"].create(
            {
                "name": "Invoice User",
                "login": "invoice.user@example.com",
                "email": "invoice.user@example.com",
                "company_id": self.company_data["company"].id,
                "company_ids": [Command.set(self.company_data["company"].ids)],
                "group_ids": [Command.link(self.env.ref("account.group_account_invoice").id)],
            },
        )

        invoice = self._create_invoice(
            self._line_vals(name="Line A", product=self.product_a, price_unit=100.0),
        )
        wizard = self.env["l10n_ph.discount_privilege.wizard"].with_user(invoice_user).with_context(
            active_id=invoice.id,
            active_ids=[invoice.id],
            active_model="account.move",
        ).create({"move_id": invoice.id})
        self.assertEqual(wizard.move_id, invoice)

        with self.assertRaises(Exception):
            self.env["l10n_ph.discount.privilege"].with_user(invoice_user).create(
                {
                    "name": "Should Not Create",
                    "discount_amount": 10.0,
                    "account_id": self.special_discount_account.id,
                    "company_id": self.company_data["company"].id,
                },
            )

    def test_preview_updates_in_wizard_without_writing_invoice(self):
        """Selecting privilege/scope previews SC/PWD values in the wizard immediately,
        but invoice lines are only written when the user confirms."""
        invoice = self._create_invoice(
            self._line_vals(name="Line A", product=self.product_a, price_unit=100.0),
            self._line_vals(name="Line B", product=self.product_b, price_unit=200.0),
        )

        wizard = self._create_wizard(
            invoice,
            privilege_id=self.privilege.id,
            apply_on="product_category",
            category_ids=[Command.set(self.category_a.ids)],
        )

        line_a, line_b = wizard.line_ids.sorted("id")
        self.assertTrue(line_a.has_discount_privilege)
        self.assertEqual(line_a.discount, 20.0)
        self.assertAlmostEqual(line_a.discounted_amount, 20.0)
        self.assertFalse(line_b.has_discount_privilege)

        # Preview-only mode: invoice lines are untouched until explicit confirmation.
        inv_line_a, inv_line_b = invoice.invoice_line_ids.sorted("sequence")
        self.assertFalse(inv_line_a.l10n_ph_discount_privilege_id)
        self.assertFalse(inv_line_b.l10n_ph_discount_privilege_id)
        self.assertEqual(inv_line_a.discount, 0.0)
        self.assertEqual(inv_line_b.discount, 0.0)

        wizard.action_confirm()
        self.assertEqual(inv_line_a.l10n_ph_discount_privilege_id, self.privilege)
        self.assertFalse(inv_line_b.l10n_ph_discount_privilege_id)

    def test_regular_discount_amount_from_tax_inclusive_price_difference(self):
        """Regular discount amount is correctly back-calculated for tax-inclusive
        (price-include division) lines when no SC/PWD privilege is active."""
        invoice = self._create_invoice(
            self._line_vals(
                name="Line A",
                product=self.product_a,
                quantity=2.0,
                price_unit=100.0,
                tax=self.tax_incl,
            ),
        )

        line = invoice.invoice_line_ids
        self.assertAlmostEqual(line.l10n_ph_regular_discount_amount, 35.71, places=2)
        self.assertEqual(line.l10n_ph_special_discount_amount, 0.0)

    def test_remove_line_discount_does_not_require_privilege(self):
        """Per-line SC/PWD privilege removal works even when no privilege is
        selected in the wizard"""
        invoice = self._create_invoice(
            self._line_vals(
                name="Line A",
                product=self.product_a,
                price_unit=100.0,
                discount=20.0,
                l10n_ph_discount_privilege_id=self.privilege.id,
            ),
        )

        wizard = self._create_wizard(invoice)
        # No privilege selected in wizard — removal must still succeed
        self.assertFalse(wizard.privilege_id)

        line_wizard = wizard.line_ids
        line_wizard.action_remove_line_discount()
        self.assertEqual(invoice.invoice_line_ids.discount, 0.0)
        self.assertFalse(invoice.invoice_line_ids.l10n_ph_discount_privilege_id)

        # Removal without a privilege selected must block a subsequent apply
        with self.assertRaises(UserError):
            wizard.action_confirm()

    def test_apply_requires_category_when_scope_is_product_category(self):
        """Applying privilege with 'product_category' scope but no category selected raises UserError."""
        invoice = self._create_invoice(
            self._line_vals(name="Line A", product=self.product_a, price_unit=100.0),
        )
        wizard = self._create_wizard(
            invoice,
            privilege_id=self.privilege.id,
            apply_on="product_category",
        )
        with self.assertRaises(UserError):
            wizard.action_confirm()

    def test_apply_requires_product_when_scope_is_product(self):
        """Applying privilege with 'product' scope but no product selected raises UserError."""
        invoice = self._create_invoice(
            self._line_vals(name="Line A", product=self.product_a, price_unit=100.0),
        )
        wizard = self._create_wizard(
            invoice,
            privilege_id=self.privilege.id,
            apply_on="product",
        )
        with self.assertRaises(UserError):
            wizard.action_confirm()

    def test_apply_privilege_without_tax_keeps_existing_taxes(self):
        """A SC/PWD privilege without a configured replacement tax preserves the line's
        existing taxes (e.g., 12% VAT stays); only the special discount amount is added."""
        invoice = self._create_invoice(
            self._line_vals(name="Line A", product=self.product_a, price_unit=100.0),
        )

        wizard = self._create_wizard(
            invoice,
            privilege_id=self.privilege_without_tax.id,
            apply_on="all",
        )
        wizard.action_confirm()

        line = invoice.invoice_line_ids
        self.assertEqual(line.tax_ids, self.base_tax)
        self.assertEqual(line.l10n_ph_discount_privilege_id, self.privilege_without_tax)
        self.assertAlmostEqual(line.price_subtotal, 80.0)
        self.assertAlmostEqual(line.price_total, 89.6)
        self._assert_discount_allocation(invoice, line, 20.0)

    def test_apply_privilege_clears_regular_discount(self):
        """Applying a SC/PWD privilege zeroes out any pre-existing regular (pricelist) discount;
        the privilege's special discount mechanism takes over entirely for that line."""
        regular_discount_account = self.company_data["default_account_revenue"].copy(
            {
                "name": "Regular Discount Allocation Account",
            },
        )
        # A regular discount allocation account must be configured to verify
        # that the regular discount entry disappears once the privilege is applied
        self.company_data[
            "company"
        ].account_discount_expense_allocation_id = regular_discount_account
        self.addCleanup(
            lambda: self.company_data["company"].write(
                {"account_discount_expense_allocation_id": False},
            ),
        )

        invoice = self._create_invoice(
            self._line_vals(
                name="Line A",
                product=self.product_a,
                price_unit=100.0,
                discount=10.0,
            ),
        )

        wizard = self._create_wizard(
            invoice,
            privilege_id=self.privilege_without_tax.id,
            apply_on="all",
        )
        wizard.action_confirm()

        line = invoice.invoice_line_ids
        self.assertEqual(line.discount, 20.0)
        self.assertAlmostEqual(line.l10n_ph_regular_discount_amount, 0.0)
        self.assertAlmostEqual(line.l10n_ph_special_discount_amount, 20.0)
        self.assertAlmostEqual(line.price_subtotal, 80.0)
        self.assertAlmostEqual(line.price_total, 89.6)
        self._assert_discount_allocation(invoice, line, 20.0)

    def test_remove_all_restores_original_taxes(self):
        """Bulk-removing SC/PWD privileges restores each line's original taxes and
        clears both the privilege link and the discount-allocation journal entries."""
        invoice = self._create_invoice(
            self._line_vals(name="Line A", product=self.product_a, price_unit=100.0),
        )

        wizard = self._create_wizard(
            invoice,
            privilege_id=self.privilege.id,
            apply_on="all",
        )
        wizard.action_confirm()
        self.assertEqual(invoice.invoice_line_ids.tax_ids, self.privilege.tax_id)
        self.assertTrue(
            invoice.line_ids.filtered(
                lambda line_item: line_item.display_type == "discount",
            ),
        )

        wizard.action_remove_all()
        self.assertEqual(invoice.invoice_line_ids.tax_ids, self.base_tax)
        self.assertFalse(invoice.invoice_line_ids.l10n_ph_discount_privilege_id)
        self.assertFalse(
            invoice.invoice_line_ids.l10n_ph_discount_privilege_previous_tax_ids,
        )
        self.assertFalse(
            invoice.line_ids.filtered(
                lambda line_item: line_item.display_type == "discount",
            ),
        )
        self.assertAlmostEqual(invoice.amount_total, 112.0)

    def test_remove_all_restores_original_discount(self):
        """Removing SC/PWD privilege restores the line's pre-privilege discount
        (e.g., a 10% SO pricelist discount overridden by the privilege comes back)."""
        invoice = self._create_invoice(
            self._line_vals(
                name="Line A",
                product=self.product_a,
                price_unit=100.0,
                discount=10.0,
            ),
        )

        wizard = self._create_wizard(
            invoice,
            privilege_id=self.privilege.id,
            apply_on="all",
        )
        wizard.action_confirm()
        # Privilege overrides the 10% pricelist discount with the privilege discount %
        self.assertEqual(invoice.invoice_line_ids.discount, 20.0)

        wizard.action_remove_all()
        # Original 10% discount must be restored from the stored baseline
        self.assertEqual(invoice.invoice_line_ids.discount, 10.0)

    def test_cannot_add_invoice_line_when_discount_privilege_is_applied(self):
        """Adding new lines to a privileged invoice is blocked to ensure every line
        goes through the privilege evaluation workflow before the invoice is confirmed."""
        invoice = self._create_invoice(
            self._line_vals(name="Line A", product=self.product_a, price_unit=100.0),
        )

        wizard = self._create_wizard(
            invoice,
            privilege_id=self.privilege.id,
            apply_on="all",
        )
        wizard.action_confirm()

        with self.assertRaises(UserError):
            invoice.write(
                {
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "Line B",
                                "product_id": self.product_b.id,
                                "account_id": self.company_data[
                                    "default_account_revenue"
                                ].id,
                                "quantity": 1.0,
                                "price_unit": 200.0,
                                "tax_ids": [Command.set(self.base_tax.ids)],
                            },
                        ),
                    ],
                },
            )

    def test_can_update_existing_invoice_line_when_discount_privilege_is_applied(self):
        """Updating fields such as quantity on an already-privileged line is still
        allowed; only adding brand-new lines is restricted."""
        invoice = self._create_invoice(
            self._line_vals(name="Line A", product=self.product_a, price_unit=100.0),
        )

        wizard = self._create_wizard(
            invoice,
            privilege_id=self.privilege.id,
            apply_on="all",
        )
        wizard.action_confirm()

        line = invoice.invoice_line_ids
        invoice.write(
            {"invoice_line_ids": [Command.update(line.id, {"quantity": 2.0})]},
        )
        self.assertEqual(line.quantity, 2.0)

    def test_special_discount_amount_uses_pre_privilege_inclusive_divisor(self):
        """When a privilege is applied to a tax-inclusive line, the helper field keeps
        the VAT-exclusive special-discount amount, while the synced discount-allocation
        journal entry follows Odoo's standard invoice discount computation.

        For a 700₱ tax-inclusive (12 % INCL) line with a 20 % PWD discount:
          - VAT-exclusive helper amount = 700 / 1.12 x 0.20 = 125.00
          - Standard JE allocation      = 700 x 0.20 = 140.00
        """
        invoice = self._create_invoice(
            self._line_vals(
                name="Line A",
                product=self.product_a,
                price_unit=700.0,
                tax=self.tax_incl,
            ),
        )

        wizard = self._create_wizard(
            invoice,
            privilege_id=self.privilege.id,
            apply_on="all",
        )
        wizard.action_confirm()

        line = invoice.invoice_line_ids
        # 700 / 1.12 * 0.20 = 125, NOT 700 * 0.20 = 140
        self.assertAlmostEqual(line.l10n_ph_special_discount_amount, 125.0, places=2)
        self._assert_discount_allocation(invoice, line, 140.0)

    def test_special_discount_amount_uses_group_tax_vat_rate_fallback(self):
        """When a privilege with a group tax that contains a VAT-removal child is applied
        to a line that originally had a price-EXCLUSIVE tax, the special discount amount
        must still use the VAT rate embedded in the group-tax formulas (12 %), not 1.0.

        This covers the common real-world scenario where a product carries the standard
        price-exclusive 12 % VAT (l10n_ph_tax_sale_12) but the SC/PWD group tax group
        assumes VAT-inclusive shelf pricing.

        For a 700₱ price-exclusive line (original tax: 12 % excl.) with a 20 % PWD:
          - The SC/PWD group tax formula recovers 700 as the base amount
          - VAT rate inferred from the group tax child with amount = -12 → divisor = 1.12
          - Special discount = 700 / 1.12 x 0.20 = 125.00  (NOT 700 x 0.20 = 140)
        """
        # Build a minimal SC/PWD-style group tax: one code child acting as VAT-removal
        # (negative amount = 12 % VAT rate) so the fallback can infer the divisor.
        vat_removal_child = self._create_tax(
            "VAT Removal (test)",
            -12,
            amount_type="code",
            type_tax_use="none",
        )
        group_tax = self.env["account.tax"].create(
            {
                "name": "SC/PWD Group Tax (test)",
                "amount_type": "group",
                "type_tax_use": "sale",
                "children_tax_ids": [Command.set(vat_removal_child.ids)],
            },
        )
        privilege_with_group_tax = (
            self.env["l10n_ph.discount.privilege"]
            .sudo()
            .create(
                {
                    "name": "PWD Group Tax Privilege",
                    "discount_amount": 20.0,
                    "tax_id": group_tax.id,
                    "account_id": self.special_discount_account.id,
                },
            )
        )

        invoice = self._create_invoice(
            self._line_vals(name="Line A", product=self.product_a, price_unit=700.0),
        )

        wizard = self._create_wizard(
            invoice,
            privilege_id=privilege_with_group_tax.id,
            apply_on="all",
        )
        wizard.action_confirm()

        line = invoice.invoice_line_ids
        # Fallback must infer 12 % from the group-tax child (amount = -12).
        # 700 / 1.12 x 0.20 = 125, NOT 700 x 0.20 = 140
        self.assertAlmostEqual(line.l10n_ph_special_discount_amount, 125.0, places=2)

    def test_apply_vat_incl_privilege_maps_tax_exclusive_unit_price(self):
        """Applying a PH-style VAT-inclusive SC privilege on a 12 % tax-exclusive line
        maps the working unit price to VAT-inclusive basis so the result is 1120 → 1000 → 800."""
        vat_incl_formula_tax = self._create_tax(
            "12% VAT INCL for SC/PWD (test)",
            0,
            amount_type="code",
            type_tax_use="none",
            price_include_override="tax_included",
            formula="(price_unit - ((price_unit / (1 - discount / 100.0)) / 1.12)) * quantity",
        )
        vat_removal_tax = self._create_tax(
            "VAT Discount (test)",
            -12,
            amount_type="code",
            type_tax_use="none",
            price_include_override="tax_excluded",
            formula="-((price_unit / (1 - discount / 100.0)) * (12.0 / 112.0)) * quantity",
        )
        sc_adjustment_tax = self._create_tax(
            "Senior Citizen Discount (test)",
            0,
            amount_type="code",
            type_tax_use="none",
            price_include_override="tax_excluded",
            formula="((price_unit / (1 - discount / 100.0) * discount / 100.0) - ((price_unit / (1 - discount / 100.0) / 1.12) * discount / 100.0)) * quantity",
        )
        vat_exempt_child = self._create_tax(
            "0% EXEMPT FOR SC/PWD USE (test)",
            0,
            type_tax_use="none",
        )
        privilege_group_tax = self.env["account.tax"].create(
            {
                "name": "VAT Exempt w/ SC Discount (test)",
                "amount_type": "group",
                "type_tax_use": "sale",
                "children_tax_ids": [
                    Command.set(
                        (
                            vat_incl_formula_tax
                            + vat_removal_tax
                            + sc_adjustment_tax
                            + vat_exempt_child
                        ).ids,
                    ),
                ],
            },
        )
        privilege = (
            self.env["l10n_ph.discount.privilege"]
            .sudo()
            .create(
                {
                    "name": "SC VAT-INCL Template Style",
                    "discount_amount": 20.0,
                    "tax_id": privilege_group_tax.id,
                    "account_id": self.special_discount_account.id,
                },
            )
        )

        invoice = self._create_invoice(
            self._line_vals(name="Line A", product=self.product_a, price_unit=1000.0),
        )
        self.assertAlmostEqual(invoice.amount_untaxed, 1000.0)
        self.assertAlmostEqual(invoice.amount_total, 1120.0)

        wizard = self._create_wizard(
            invoice,
            privilege_id=privilege.id,
            apply_on="all",
        )
        self.assertAlmostEqual(wizard.line_ids.discounted_amount, 200.0, places=2)

        wizard.action_confirm()

        line = invoice.invoice_line_ids
        self.assertEqual(line.tax_ids, privilege_group_tax)
        self.assertAlmostEqual(line.price_unit, 1000.0, places=2)
        self.assertAlmostEqual(line.l10n_ph_internal_price_unit, 1120.0, places=2)
        self.assertAlmostEqual(line.l10n_ph_special_discount_amount, 200.0, places=2)
        self.assertAlmostEqual(invoice.amount_untaxed, 1000.0, places=2)
        self.assertAlmostEqual(invoice.amount_total, 800.0, places=2)
        self._assert_discount_allocation(invoice, line, 200.0)

        wizard.action_remove_all()
        self.assertEqual(line.tax_ids, self.base_tax)
        self.assertAlmostEqual(line.price_unit, 1000.0, places=2)
        self.assertAlmostEqual(line.l10n_ph_internal_price_unit, 0.0, places=2)
        self.assertAlmostEqual(invoice.amount_untaxed, 1000.0, places=2)
        self.assertAlmostEqual(invoice.amount_total, 1120.0, places=2)

    def test_onchange_privilege_prefills_category_scope(self):
        """Selecting a privilege that has predefined product categories auto-switches
        the scope to 'product_category' and pre-populates the matching categories."""
        invoice = self._create_invoice(
            self._line_vals(name="Line A", product=self.product_a, price_unit=100.0),
        )

        wizard = self._create_wizard(invoice)
        wizard.privilege_id = self.privilege_with_categories
        wizard._onchange_privilege_id()
        self.assertEqual(wizard.apply_on, "product_category")
        self.assertEqual(wizard.category_ids, self.category_a)

    def test_apply_on_credit_note(self):
        """SC/PWD privilege can be applied to credit notes (out_refund) identically."""
        credit_note = self.env["account.move"].create(
            {
                "move_type": "out_refund",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    Command.create(
                        self._line_vals(name="Refund Line", price_unit=100.0),
                    ),
                ],
            },
        )

        wizard = self._create_wizard(
            credit_note,
            privilege_id=self.privilege.id,
            apply_on="all",
        )
        wizard.action_confirm()

        line = credit_note.invoice_line_ids
        self.assertEqual(line.l10n_ph_discount_privilege_id, self.privilege)
        self.assertEqual(line.discount, 20.0)
        self.assertEqual(line.tax_ids, self.privilege.tax_id)
        self.assertAlmostEqual(line.l10n_ph_special_discount_amount, 20.0)

    def test_apply_product_scope(self):
        """SC/PWD privilege with 'product' scope applies only to matching product."""
        invoice = self._create_invoice(
            self._line_vals(name="Line A", product=self.product_a, price_unit=100.0),
            self._line_vals(name="Line B", product=self.product_b, price_unit=200.0),
        )

        wizard = self._create_wizard(
            invoice,
            privilege_id=self.privilege.id,
            apply_on="product",
            product_ids=[Command.set([self.product_a.id])],
        )
        wizard.action_confirm()

        line_a, line_b = invoice.invoice_line_ids.sorted("sequence")
        self.assertEqual(line_a.l10n_ph_discount_privilege_id, self.privilege)
        self.assertFalse(line_b.l10n_ph_discount_privilege_id)
        self.assertEqual(line_a.discount, 20.0)
        self.assertEqual(line_b.discount, 0.0)

    def test_apply_with_quantity_greater_than_one(self):
        """Special discount amount scales correctly with quantity."""
        invoice = self._create_invoice(
            self._line_vals(
                name="Line A",
                product=self.product_a,
                price_unit=100.0,
                quantity=3.0,
            ),
        )

        wizard = self._create_wizard(
            invoice,
            privilege_id=self.privilege.id,
            apply_on="all",
        )
        wizard.action_confirm()

        line = invoice.invoice_line_ids
        # 100 * 3 * 0.20 = 60
        self.assertAlmostEqual(line.l10n_ph_special_discount_amount, 60.0)
        self.assertAlmostEqual(line.price_subtotal, 240.0)

    def test_copy_invoice_copies_privilege(self):
        """Duplicating an invoice with applied privilege carries over all privilege
        data, enabling proper restoration on the copy."""
        invoice = self._create_invoice(
            self._line_vals(name="Line A", product=self.product_a, price_unit=100.0),
        )
        wizard = self._create_wizard(
            invoice,
            privilege_id=self.privilege.id,
            apply_on="all",
        )
        wizard.action_confirm()
        self.assertTrue(invoice.invoice_line_ids.l10n_ph_discount_privilege_id)
        orig_line = invoice.invoice_line_ids

        copied = invoice.copy()
        line = copied.invoice_line_ids
        self.assertEqual(line.l10n_ph_discount_privilege_id, orig_line.l10n_ph_discount_privilege_id)
        self.assertEqual(
            line.l10n_ph_discount_privilege_previous_tax_ids.ids,
            orig_line.l10n_ph_discount_privilege_previous_tax_ids.ids,
        )
        self.assertEqual(
            line.l10n_ph_discount_privilege_previous_discount,
            orig_line.l10n_ph_discount_privilege_previous_discount,
        )

        # Verify removal on the copy properly restores original state
        remove_wizard = self.env["l10n_ph.discount_privilege.wizard"].create({
            "move_id": copied.id,
        })
        remove_wizard.action_remove_all()
        self.assertFalse(line.l10n_ph_discount_privilege_id)
        self.assertEqual(line.tax_ids, self.base_tax)

    def test_cannot_apply_on_posted_invoice(self):
        """Applying privilege on a posted (non-draft) invoice raises UserError."""
        invoice = self._create_invoice(
            self._line_vals(name="Line A", product=self.product_a, price_unit=100.0),
        )
        invoice.action_post()

        wizard = self._create_wizard(
            invoice,
            privilege_id=self.privilege.id,
            apply_on="all",
        )
        with self.assertRaises(UserError):
            wizard.action_confirm()

    def test_cannot_remove_on_posted_invoice(self):
        """Removing privilege on a posted invoice raises UserError."""
        invoice = self._create_invoice(
            self._line_vals(name="Line A", product=self.product_a, price_unit=100.0),
        )
        wizard = self._create_wizard(
            invoice,
            privilege_id=self.privilege.id,
            apply_on="all",
        )
        wizard.action_confirm()
        invoice.action_post()

        with self.assertRaises(UserError):
            wizard.action_remove_all()

    def test_reapply_different_privilege(self):
        """Re-applying a different privilege updates the discount amount but preserves
        the original pre-privilege state for restoration."""
        invoice = self._create_invoice(
            self._line_vals(
                name="Line A",
                product=self.product_a,
                price_unit=100.0,
                discount=10.0,
            ),
        )

        # Apply first privilege (20%)
        wizard = self._create_wizard(
            invoice,
            privilege_id=self.privilege.id,
            apply_on="all",
        )
        wizard.action_confirm()
        line = invoice.invoice_line_ids
        self.assertEqual(line.discount, 20.0)
        self.assertEqual(line.l10n_ph_discount_privilege_previous_discount, 10.0)

        # Re-apply different privilege without tax (still 20% but different privilege)
        wizard2 = self._create_wizard(
            invoice,
            privilege_id=self.privilege_without_tax.id,
            apply_on="all",
        )
        wizard2.action_confirm()
        self.assertEqual(line.l10n_ph_discount_privilege_id, self.privilege_without_tax)
        self.assertEqual(line.discount, 20.0)
        # Original state should still reference the pre-first-privilege state
        self.assertEqual(line.l10n_ph_discount_privilege_previous_discount, 10.0)

        # Removing should restore to original 10%
        wizard2.action_remove_all()
        self.assertEqual(line.discount, 10.0)
        self.assertFalse(line.l10n_ph_discount_privilege_id)

    def test_privilege_model_constraint_positive_amount(self):
        """Discount privilege requires a discount amount between 0 and 100."""

        with self.assertRaises(ValidationError):
            self.env["l10n_ph.discount.privilege"].sudo().create(
                {
                    "name": "Invalid Zero",
                    "discount_amount": 0.0,
                    "account_id": self.special_discount_account.id,
                },
            )

        with self.assertRaises(ValidationError):
            self.env["l10n_ph.discount.privilege"].sudo().create(
                {
                    "name": "Invalid Negative",
                    "discount_amount": -5.0,
                    "account_id": self.special_discount_account.id,
                },
            )

        with self.assertRaises(ValidationError):
            self.env["l10n_ph.discount.privilege"].sudo().create(
                {
                    "name": "Invalid Over 100",
                    "discount_amount": 101.0,
                    "account_id": self.special_discount_account.id,
                },
            )

    def test_privilege_not_applied_on_vendor_bill(self):
        """The l10n_ph_has_discount_privilege field is False for purchase documents."""
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Vendor Line",
                            "product_id": self.product_a.id,
                            "account_id": self.company_data[
                                "default_account_expense"
                            ].id,
                            "quantity": 1.0,
                            "price_unit": 100.0,
                        },
                    ),
                ],
            },
        )
        self.assertFalse(bill.l10n_ph_has_discount_privilege)

    def test_has_discount_privilege_computed_field(self):
        """The l10n_ph_has_discount_privilege computed field correctly reflects state."""
        invoice = self._create_invoice(
            self._line_vals(name="Line A", product=self.product_a, price_unit=100.0),
        )
        self.assertFalse(invoice.l10n_ph_has_discount_privilege)

        wizard = self._create_wizard(
            invoice,
            privilege_id=self.privilege.id,
            apply_on="all",
        )
        wizard.action_confirm()
        self.assertTrue(invoice.l10n_ph_has_discount_privilege)

        wizard.action_remove_all()
        self.assertFalse(invoice.l10n_ph_has_discount_privilege)

    @classmethod
    def _create_tax(
        cls,
        name,
        amount,
        amount_type="percent",
        type_tax_use="sale",
        tax_exigibility="on_invoice",
        **kwargs,
    ):
        vals = {
            "name": name,
            "amount": amount,
            "amount_type": amount_type,
            "type_tax_use": type_tax_use,
            "tax_exigibility": tax_exigibility,
            "invoice_repartition_line_ids": [
                Command.create({"factor_percent": 100, "repartition_type": "base"}),
                Command.create({"factor_percent": 100, "repartition_type": "tax"}),
            ],
            "refund_repartition_line_ids": [
                Command.create({"factor_percent": 100, "repartition_type": "base"}),
                Command.create({"factor_percent": 100, "repartition_type": "tax"}),
            ],
            **kwargs,
        }
        return cls.env["account.tax"].create(vals)
