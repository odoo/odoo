# Part of Odoo. See LICENSE file for full copyright and licensing details.

import psycopg2

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command, Date
from odoo.tests import Form, tagged
from odoo.tools import mute_logger

from odoo.addons.l10n_ph.tests.common import TestPhCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestDiscountPrivilegeWizard(TestPhCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        ChartTemplate = cls.env["account.chart.template"].with_company(
            cls.company_data["company"],
        )
        cls.tax_sale_12 = ChartTemplate.ref("l10n_ph_tax_sale_12")
        cls.tax_sale_0_exempt = ChartTemplate.ref("l10n_ph_tax_sale_0_exempt")
        cls.tax_sale_0_exempt_sc_pwd = ChartTemplate.ref("l10n_ph_tax_sale_0_exempt_sc_pwd")
        cls.fpos_sc_pwd = ChartTemplate.ref("l10n_ph_fiscal_position_discount_privileges")
        cls.base_tax = cls.tax_sale_12

        cls.tax_incl = cls._create_tax("12% VAT INCL", 12, price_include_override="tax_included")
        cls.tax_sale_0_exempt_sc_pwd.write(
            {"original_tax_ids": [Command.link(cls.tax_incl.id)]},
        )
        cls.special_discount_account = cls.company_data["default_account_revenue"].copy(
            {"name": "Discount Privilege Account"},
        )
        cls.privilege = (
            cls.env["l10n_ph.discount.privilege"]
            .sudo()
            .create(
                {
                    "name": "Senior Citizen",
                    "discount_amount": 0.2,
                    "fiscal_position_id": cls.fpos_sc_pwd.id,
                    "account_id": cls.special_discount_account.id,
                },
            )
        )
        cls.privilege_without_tax = (
            cls.env["l10n_ph.discount.privilege"]
            .sudo()
            .create(
                {
                    "name": "Special Discount 20% No FP",
                    "discount_type": "special",
                    "discount_amount": 0.2,
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
                    "discount_amount": 0.2,
                    "fiscal_position_id": cls.fpos_sc_pwd.id,
                    "account_id": cls.special_discount_account.id,
                    "applied_to_category_ids": [Command.set([])],
                },
            )
        )

        cls.category_a = cls.env["product.category"].create({"name": "Category A"})
        cls.category_b = cls.env["product.category"].create({"name": "Category B"})
        cls.product_a = cls.env["product.product"].create(
            {"name": "Product A", "categ_id": cls.category_a.id, "list_price": 120.0},
        )
        cls.product_b = cls.env["product.product"].create(
            {"name": "Product B", "categ_id": cls.category_b.id, "list_price": 220.0},
        )
        cls.privilege_with_categories.write(
            {"applied_to_category_ids": [Command.set(cls.category_a.ids)]},
        )

        cls.invoice = cls._create_invoice_with_lines(
            ("Line A", cls.product_a, 100.0),
            ("Line B", cls.product_b, 200.0),
        )

    # ============================================================
    #  Privilege Model Constraints
    # ============================================================

    def test_privilege_model_constraint_positive_amount(self):
        for amount in (0.0, -0.05, 1.1):
            with self.subTest(discount_amount=amount), self.assertRaises(ValidationError):
                self._create_privilege(f"Invalid {amount}", amount)

    def test_privilege_unique_name_per_company(self):
        self._create_privilege("Duplicate Name", 0.2)
        with self.assertRaises(psycopg2.errors.UniqueViolation), mute_logger("odoo.sql_db"):
            self._create_privilege("Duplicate Name", 0.3)

    def test_privilege_copy_appends_copy_suffix(self):
        priv_copy = self.privilege.copy()
        self.assertEqual(priv_copy.name, "Senior Citizen (copy)")
        self.assertEqual(priv_copy.discount_amount, self.privilege.discount_amount)
        self.assertEqual(priv_copy.account_id, self.privilege.account_id)

    def test_privilege_in_use_cannot_be_deleted(self):
        invoice = self.invoice
        self._apply_privilege(invoice, privilege_id=self.privilege.id, apply_on="all")
        # Deleting a privilege in use must fail at SQL level. Fresh DBs raise
        # RestrictViolation, older dumps may raise ForeignKeyViolation.
        with (
            self.assertRaises(
                (psycopg2.errors.RestrictViolation, psycopg2.errors.ForeignKeyViolation),
            ),
            mute_logger("odoo.sql_db"),
        ):
            self.privilege.unlink()
        self.privilege.active = False
        self.assertFalse(self.privilege.active)

    # ============================================================
    #  Wizard flow — preview and cancel / confirm
    # ============================================================

    def test_wizard_preview_then_cancel_then_confirm(self):
        invoice = self.invoice
        wizard = self._create_wizard(
            invoice,
            privilege_id=self.privilege.id,
            apply_on="product_category",
            category_ids=[Command.set(self.category_a.ids)],
        )
        line_a, line_b = wizard.line_ids.sorted("id")
        self.assertTrue(line_a.has_discount_privilege)
        self.assertEqual(line_a.discount, 20.0)
        self.assertAlmostEqual(line_a.discount_amount, 20.0)
        self.assertFalse(line_b.has_discount_privilege)

        # Without confirm, nothing is written on the invoice.
        inv_line_a, inv_line_b = invoice.invoice_line_ids.sorted("sequence")
        self.assertFalse(inv_line_a.l10n_ph_discount_privilege_id)
        self.assertFalse(inv_line_b.l10n_ph_discount_privilege_id)
        self.assertEqual(inv_line_a.discount, 0.0)
        self.assertEqual(inv_line_b.discount, 0.0)
        self.assertEqual(inv_line_a.tax_ids, self.base_tax)
        self.assertEqual(inv_line_b.tax_ids, self.base_tax)

        # Confirm writes only matching lines.
        wizard.action_confirm()
        self.assertEqual(inv_line_a.l10n_ph_discount_privilege_id, self.privilege)
        self.assertEqual(inv_line_a.discount, 20.0)
        self.assertFalse(inv_line_b.l10n_ph_discount_privilege_id)
        self.assertEqual(inv_line_b.discount, 0.0)

    def test_wizard_remove_line_then_cancel_then_confirm(self):
        invoice = self.invoice
        wizard = self._create_wizard(invoice, privilege_id=self.privilege.id, apply_on="all")
        wizard.action_confirm()

        line_a, line_b = invoice.invoice_line_ids.sorted("sequence")
        self.assertEqual(line_a.l10n_ph_discount_privilege_id, self.privilege)
        self.assertEqual(line_b.l10n_ph_discount_privilege_id, self.privilege)

        wizard = self._create_wizard(invoice)
        wizard.line_ids.filtered(
            lambda wiz_line: wiz_line.invoice_line_id == line_a,
        ).action_remove_line_discount()

        # Marking removal only updates the preview; cancel keeps both lines.
        self.assertEqual(line_a.l10n_ph_discount_privilege_id, self.privilege)
        self.assertEqual(line_b.l10n_ph_discount_privilege_id, self.privilege)
        self.assertEqual(line_a.discount, 20.0)
        self.assertEqual(line_b.discount, 20.0)

        # Confirm applies removal on line A only.
        wizard.action_confirm()
        self.assertFalse(line_a.l10n_ph_discount_privilege_id)
        self.assertEqual(line_a.discount, 0.0)
        self.assertEqual(line_a.tax_ids, self.base_tax)
        self.assertEqual(line_b.l10n_ph_discount_privilege_id, self.privilege)
        self.assertEqual(line_b.discount, 20.0)

    def test_has_discount_privilege_computed_field(self):
        invoice = self.invoice
        self.assertFalse(invoice.l10n_ph_has_discount_privilege)

        wizard = self._create_wizard(invoice, privilege_id=self.privilege.id, apply_on="all")
        wizard.action_confirm()
        self.assertTrue(invoice.l10n_ph_has_discount_privilege)

        wizard.action_remove_all()
        self.assertFalse(invoice.l10n_ph_has_discount_privilege)

    # ============================================================
    #  Apply Scopes — all / product / product_category
    # ============================================================

    def test_apply_product_and_category_scopes_match_lines(self):
        invoice = self.invoice
        for apply_on, apply_values in (
            (
                "product",
                {"product_ids": [Command.set([self.product_a.id])]},
            ),
            (
                "product_category",
                {"category_ids": [Command.set(self.category_a.ids)]},
            ),
        ):
            with self.subTest(apply_on=apply_on):
                self._apply_privilege(
                    invoice,
                    privilege_id=self.privilege.id,
                    apply_on=apply_on,
                    **apply_values,
                )

                line_a, line_b = invoice.invoice_line_ids.sorted("sequence")
                self.assertEqual(line_a.discount, 20.0)
                self.assertEqual(line_a.l10n_ph_discount_privilege_id, self.privilege)
                self.assertEqual(line_b.discount, 0.0)
                self.assertFalse(line_b.l10n_ph_discount_privilege_id)
                self.assertEqual(line_b.tax_ids, self.base_tax)

                self._create_wizard(invoice).action_remove_all()

    def test_apply_product_category_scope_matches_child_categories(self):
        # Parent-category matching includes child categories for both wizard
        # scope and privilege restriction.
        parent_category = self.env["product.category"].create({"name": "Parent Category"})
        child_category = self.env["product.category"].create(
            {"name": "Child Category", "parent_id": parent_category.id},
        )
        child_product = self.env["product.product"].create(
            {"name": "Child Product", "categ_id": child_category.id, "list_price": 100.0},
        )
        other_product = self.env["product.product"].create(
            {"name": "Other Product", "categ_id": self.category_b.id, "list_price": 100.0},
        )
        invoice = self._create_invoice_with_lines(
            ("Child", child_product, 100.0),
            ("Other", other_product, 100.0),
        )

        # Parent category scope.
        wizard = self._create_wizard(
            invoice,
            privilege_id=self.privilege.id,
            apply_on="product_category",
            category_ids=[Command.set(parent_category.ids)],
        )
        line_child_wiz, line_other_wiz = wizard.line_ids.sorted("id")
        self.assertTrue(line_child_wiz.has_discount_privilege)
        self.assertFalse(line_other_wiz.has_discount_privilege)
        wizard.action_confirm()

        line_child, line_other = invoice.invoice_line_ids.sorted("sequence")
        self.assertEqual(line_child.l10n_ph_discount_privilege_id, self.privilege)
        self.assertEqual(line_child.discount, 20.0)
        self.assertFalse(line_other.l10n_ph_discount_privilege_id)

        # Parent category restriction with scope "all".
        priv = self._create_privilege(
            "Parent Category Only",
            0.2,
            applied_to_category_ids=[Command.set(parent_category.ids)],
        )
        self._apply_privilege(invoice, privilege_id=priv.id, apply_on="all")
        line_child, line_other = invoice.invoice_line_ids.sorted("sequence")
        self.assertEqual(line_child.l10n_ph_discount_privilege_id, priv)
        self.assertEqual(line_child.discount, 20.0)
        self.assertFalse(line_other.l10n_ph_discount_privilege_id)

    def test_wizard_category_scope_preview_via_onchange(self):
        """Setting the category scope must refresh the previews through onchange."""
        invoice = self.invoice
        wizard = self._create_wizard(invoice, privilege_id=self.privilege.id)
        with Form(wizard) as form:
            form.apply_on = "product_category"
            form.category_ids = self.category_a
            line_a = form.line_ids.edit(0)
            line_b = form.line_ids.edit(1)
            self.assertTrue(line_a.has_discount_privilege)
            self.assertEqual(line_a.discount_amount, 20.0)
            self.assertFalse(line_b.has_discount_privilege)
            self.assertEqual(line_b.discount_amount, 0.0)

    def test_wizard_privilege_onchange_autoselects_categories(self):
        """Selecting a category-scoped privilege in the wizard must switch the
        scope to 'Product Categories' and pre-select the privilege's
        categories (simulated as the web client does, through onchanges).
        Switching to a different, category-less privilege afterwards, within
        the same editing session, does not reset an already-selected scope."""
        wizard = self._create_wizard(self.invoice)
        with Form(wizard) as form:
            form.privilege_id = self.privilege_with_categories
            self.assertEqual(form.apply_on, "product_category")
            self.assertEqual(form.category_ids.ids, self.category_a.ids)

            form.privilege_id = self.privilege
            self.assertEqual(form.apply_on, "product_category")
            self.assertEqual(form.category_ids.ids, self.category_a.ids)
        self.assertEqual(wizard.category_ids, self.category_a)

    def test_fp_privilege_skips_lines_without_mappable_taxes(self):
        """A fiscal-position privilege only applies to lines whose taxes it
        maps: VAT-exempt and zero-rated lines keep their taxes and receive
        no statutory discount."""
        invoice = self._create_invoice_with_lines(
            ("Line VAT", self.product_a, 100.0, {"tax_ids": self.tax_sale_12}),
            ("Line Exempt", self.product_b, 100.0, {"tax_ids": self.tax_sale_0_exempt}),
        )
        vat_line = invoice.invoice_line_ids.filtered(lambda line: line.product_id == self.product_a)
        exempt_line = invoice.invoice_line_ids.filtered(lambda line: line.product_id == self.product_b)

        # The preview already excludes the exempt line.
        wizard = self._create_wizard(invoice, privilege_id=self.privilege.id)
        self.assertTrue(wizard._get_preview_privilege_for_line(vat_line))
        self.assertFalse(wizard._get_preview_privilege_for_line(exempt_line))

        self._apply_privilege(invoice, privilege_id=self.privilege.id, apply_on="all")
        self.assertEqual(vat_line.tax_ids, self.tax_sale_0_exempt_sc_pwd)
        self.assertEqual(vat_line.discount, 20.0)
        self.assertEqual(exempt_line.tax_ids, self.tax_sale_0_exempt)
        self.assertEqual(exempt_line.discount, 0.0)
        self.assertFalse(exempt_line.l10n_ph_discount_privilege_id)

        # Explicitly targeting the exempt line applies nothing.
        with self.assertRaises(UserError):
            self._apply_privilege(
                invoice,
                privilege_id=self.privilege.id,
                apply_on="product",
                product_ids=[Command.set([self.product_b.id])],
            )

    def test_apply_requires_scope_selection(self):
        invoice = self.invoice
        for apply_on in ("product_category", "product"):
            with self.subTest(apply_on=apply_on):
                wizard = self._create_wizard(invoice, privilege_id=self.privilege.id, apply_on=apply_on)
                with self.assertRaises(UserError):
                    wizard.action_confirm()

    # ============================================================
    #  Tax Mapping via Fiscal Position
    # ============================================================

    def test_apply_fp_maps_taxes_and_discount_math(self):
        invoice = self._single_line_invoice()
        self._apply_privilege(invoice, privilege_id=self.privilege.id, apply_on="all")

        line = invoice.invoice_line_ids
        self.assertEqual(line.tax_ids, self.tax_sale_0_exempt_sc_pwd)
        self.assertAlmostEqual(line.price_subtotal, 80.0)
        self.assertAlmostEqual(line.price_total, 80.0)
        self.assertAlmostEqual(line.l10n_ph_special_discount_amount, 20.0)
        self.assertAlmostEqual(invoice.amount_total, 80.0)

    def test_fp_maps_multiple_taxes(self):
        tax_12 = self.base_tax
        tax_local = self._create_tax("Local Tax", 2.0)

        fpos = self.env["account.fiscal.position"].create({"name": "Multi-tax FP"})
        sc_pwd_tax = self.tax_sale_0_exempt_sc_pwd
        sc_pwd_tax.write({"original_tax_ids": [Command.set([tax_12.id, tax_local.id])]})
        fpos.write({"tax_ids": [Command.set([sc_pwd_tax.id])]})
        self.fpos_sc_pwd.write({"tax_ids": [Command.set([sc_pwd_tax.id])]})

        priv = self._create_privilege("Multi-tax FP", 0.2, fiscal_position_id=fpos)

        invoice = self._create_invoice_with_lines(
            ("Line A", self.product_a, 100.0, {"tax_ids": tax_12 + tax_local}),
        )
        self._apply_privilege(invoice, privilege_id=priv.id, apply_on="all")

        line = invoice.invoice_line_ids
        self.assertEqual(line.tax_ids, self.tax_sale_0_exempt_sc_pwd)
        self.assertAlmostEqual(line.l10n_ph_special_discount_amount, 20.0, places=2)

    def test_fp_with_non_1_to_1_mapping(self):
        tax_dest1 = self._create_tax("Dest 1", 0.0)
        tax_dest2 = self._create_tax("Dest 2", 0.0)

        fpos = self.env["account.fiscal.position"].create({"name": "Non-1:1 FP"})
        tax_dest1.write({"original_tax_ids": [Command.set([self.base_tax.id])]})
        tax_dest2.write({"original_tax_ids": [Command.set([self.base_tax.id])]})
        fpos.write({"tax_ids": [Command.set([tax_dest1.id, tax_dest2.id])]})

        priv = self._create_privilege("Non-1:1 FP", 0.2, fiscal_position_id=fpos)

        invoice = self._create_invoice_with_lines(
            ("Line A", self.product_a, 100.0),
        )
        self._apply_privilege(invoice, privilege_id=priv.id, apply_on="all")

        line = invoice.invoice_line_ids
        self.assertEqual(len(line.tax_ids), 2)
        self.assertIn(tax_dest1, line.tax_ids)
        self.assertIn(tax_dest2, line.tax_ids)

    # ============================================================
    #  Discount Math — tax-inclusive / tax-exclusive / VAT-able
    # ============================================================

    def test_apply_privilege_without_tax_keeps_existing_taxes(self):
        invoice = self._single_line_invoice()
        self._apply_privilege(
            invoice,
            privilege_id=self.privilege_without_tax.id,
            apply_on="all",
        )

        line = invoice.invoice_line_ids
        self.assertEqual(line.tax_ids, self.base_tax)
        self.assertEqual(line.l10n_ph_discount_privilege_id, self.privilege_without_tax)
        self.assertAlmostEqual(line.price_subtotal, 80.0)
        self.assertAlmostEqual(line.price_total, 89.6)
        self._assert_discount_allocation(invoice, line, 22.4)

    def test_special_privilege_on_tax_included_line(self):
        for discount_amount, expected_amount in ((0.2, 100.0), (0.05, 25.0)):
            with self.subTest(discount_amount=discount_amount):
                privilege = self._create_privilege(
                    f"Special Discount Tax-Incl {discount_amount * 100:.0f}%",
                    discount_amount,
                    discount_type="special",
                )
                invoice = self._create_invoice_with_lines(
                    ("Line A", self.product_a, 500.0, {"tax_ids": self.tax_incl}),
                )
                self._apply_privilege(
                    invoice, privilege_id=privilege.id, apply_on="all",
                )

                line = invoice.invoice_line_ids
                self.assertEqual(line.discount, discount_amount * 100)
                self.assertEqual(line.tax_ids, self.tax_incl)
                self.assertAlmostEqual(
                    line.l10n_ph_special_discount_amount,
                    expected_amount,
                    places=2,
                )
                self._assert_discount_allocation(invoice, line, expected_amount)

    def test_special_discount_amount_on_tax_inclusive_line(self):
        invoice = self._create_invoice_with_lines(
            ("Line A", self.product_a, 700.0, {"tax_ids": self.tax_incl}),
        )
        self._apply_privilege(invoice, privilege_id=self.privilege.id, apply_on="all")

        line = invoice.invoice_line_ids
        self.assertAlmostEqual(line.l10n_ph_special_discount_amount, 125.0, places=2)
        self.assertAlmostEqual(line.price_subtotal, 500.0, places=2)
        self.assertAlmostEqual(line.price_total, 500.0, places=2)
        self.assertAlmostEqual(invoice.amount_untaxed, 500.0, places=2)
        self.assertAlmostEqual(invoice.amount_total, 500.0, places=2)
        self._assert_discount_allocation(invoice, line, 125.0)

    def test_fp_privilege_on_standard_vat(self):
        for document_tax_mode, price_unit, expected in (
            ("tax_included", 750.0, (669.64, 535.71, 133.93)),
            ("tax_excluded", 1000.0, (1000.0, 800.0, 200.0)),
        ):
            with self.subTest(document_tax_mode=document_tax_mode):
                expected_unit, expected_subtotal, expected_amount = expected
                invoice = self._create_invoice_with_lines(
                    (
                        "Line A",
                        self.product_a,
                        price_unit,
                        {"tax_ids": self.tax_sale_12},
                    ),
                    document_tax_mode=document_tax_mode,
                )
                self._apply_privilege(
                    invoice,
                    privilege_id=self.privilege.id,
                    apply_on="all",
                )

                line = invoice.invoice_line_ids
                self.assertEqual(line.discount, 20.0)
                self.assertAlmostEqual(line.price_unit, expected_unit, places=2)
                self.assertAlmostEqual(line.price_subtotal, expected_subtotal, places=2)
                self.assertAlmostEqual(invoice.amount_total, expected_subtotal, places=2)
                self.assertAlmostEqual(
                    line.l10n_ph_special_discount_amount,
                    expected_amount,
                    places=2,
                )
                self._assert_discount_allocation(invoice, line, expected_amount)

    def test_apply_privilege_on_multi_currency_invoice(self):
        # rate 2.0 means 1 EUR = 0.5 company currency (PHP).
        currency = self.setup_other_currency(
            "EUR",
            rates=[(Date.today().isoformat(), 2.0)],
        )
        invoice = self._create_invoice_with_lines(
            ("Line A", self.product_a, 100.0),
            currency_id=currency.id,
        )
        self._apply_privilege(invoice, privilege_id=self.privilege.id, apply_on="all")

        line = invoice.invoice_line_ids
        self.assertEqual(line.currency_id, currency)
        self.assertAlmostEqual(line.price_subtotal, 80.0, places=2)
        self.assertAlmostEqual(line.l10n_ph_special_discount_amount, 20.0, places=2)

        # The discount allocation keeps the foreign-currency amount and
        # converts the balance to the company currency (20 EUR = 10 PHP).
        discount_lines = invoice.line_ids.filtered(
            lambda line_item: line_item.display_type == "discount",
        )
        self.assertRecordValues(
            discount_lines.sorted("amount_currency"),
            [
                {"account_id": line.account_id.id, "amount_currency": -20.0, "balance": -10.0},
                {"account_id": self.special_discount_account.id, "amount_currency": 20.0, "balance": 10.0},
            ],
        )

    def test_special_privilege_on_tax_excluded_line(self):
        for discount_amount, price_unit, expected_amount in (
            (0.2, 1000.0, 224.0),
            (0.05, 500.0, 28.0),
        ):
            with self.subTest(discount_amount=discount_amount):
                privilege = self._create_privilege(
                    f"Special Discount Tax-Excl {discount_amount * 100:.0f}%",
                    discount_amount,
                    discount_type="special",
                )
                invoice = self._create_invoice_with_lines(
                    ("Line A", self.product_a, price_unit, {"tax_ids": self.base_tax}),
                )
                wizard = self._create_wizard(invoice, privilege_id=privilege.id, apply_on="all")
                self.assertAlmostEqual(wizard.line_ids.discount_amount, expected_amount, places=2)

                wizard.action_confirm()

                line = invoice.invoice_line_ids
                self.assertEqual(line.discount, discount_amount * 100)
                self.assertEqual(line.tax_ids, self.base_tax)
                self.assertAlmostEqual(line.price_unit, price_unit, places=2)
                self.assertAlmostEqual(
                    line.l10n_ph_special_discount_amount,
                    expected_amount,
                    places=2,
                )
                self._assert_discount_allocation(invoice, line, expected_amount)

    # ============================================================
    #  Remove Operations — single line and bulk
    # ============================================================

    def test_remove_privileges(self):
        # End-to-end: switch privileges, remove one line, then remove all.
        for document_tax_mode, price_unit in (
            ("tax_excluded", 100.0),
            ("tax_included", 750.0),
        ):
            with self.subTest(document_tax_mode=document_tax_mode):
                invoice = self._create_invoice_with_lines(
                    (
                        "Line A",
                        self.product_a,
                        price_unit,
                        {"tax_ids": self.tax_sale_12, "discount": 10.0},
                    ),
                    ("Line B", self.product_b, 200.0, {"discount": 5.0}),
                    document_tax_mode=document_tax_mode,
                )
                line_a, line_b = invoice.invoice_line_ids.sorted("sequence")

                # Apply FP privilege: taxes map to exempt SC/PWD and discount
                # replaces manual discounts.
                self._apply_privilege(invoice, privilege_id=self.privilege.id, apply_on="all")
                self.assertEqual(line_a.tax_ids, self.tax_sale_0_exempt_sc_pwd)
                self.assertEqual(line_a.discount, 20.0)
                self.assertEqual(line_a.l10n_ph_original_discount, 10.0)
                self.assertEqual(line_b.tax_ids, self.tax_sale_0_exempt_sc_pwd)
                self.assertEqual(line_b.discount, 20.0)
                self.assertEqual(line_b.l10n_ph_original_discount, 5.0)

                # Switch to no-FP privilege: reset tax mapping and price
                # adaptation.
                self._apply_privilege(invoice, privilege_id=self.privilege_without_tax.id, apply_on="all")
                self.assertEqual(line_a.l10n_ph_discount_privilege_id, self.privilege_without_tax)
                self.assertEqual(line_a.tax_ids, self.tax_sale_12)
                self.assertFalse(line_a.l10n_ph_original_tax_ids)
                self.assertAlmostEqual(line_a.price_unit, price_unit, places=2)
                self.assertEqual(line_a.l10n_ph_original_price_unit, 0.0)
                self.assertEqual(line_a.l10n_ph_original_discount, 10.0)
                self.assertEqual(line_b.tax_ids, self.tax_sale_12)

                # Switch back twice: same privilege remains idempotent.
                self._apply_privilege(invoice, privilege_id=self.privilege.id, apply_on="all")
                self._apply_privilege(invoice, privilege_id=self.privilege.id, apply_on="all")
                self.assertEqual(line_a.l10n_ph_discount_privilege_id, self.privilege)
                self.assertEqual(line_a.tax_ids, self.tax_sale_0_exempt_sc_pwd)
                self.assertEqual(line_a.discount, 20.0)
                self.assertEqual(line_a.l10n_ph_original_discount, 10.0)
                self.assertEqual(line_b.tax_ids, self.tax_sale_0_exempt_sc_pwd)

                # Remove line B without selecting a privilege: line B resets,
                # line A and its allocation remain.
                wizard = self._create_wizard(invoice)
                wizard.line_ids.filtered(
                    lambda wiz_line: wiz_line.invoice_line_id == line_b,
                ).action_remove_line_discount()
                wizard.action_confirm()
                self.assertFalse(line_b.l10n_ph_discount_privilege_id)
                self.assertEqual(line_b.discount, 5.0)
                self.assertEqual(line_b.tax_ids, self.tax_sale_12)
                self.assertAlmostEqual(line_b.price_unit, 200.0, places=2)
                self.assertEqual(line_a.l10n_ph_discount_privilege_id, self.privilege)
                self.assertEqual(line_a.discount, 20.0)
                discount_lines = invoice.line_ids.filtered(
                    lambda line_item: line_item.display_type == "discount",
                )
                self.assertEqual(len(discount_lines), 2)
                self.assertEqual(
                    {line_item.account_id for line_item in discount_lines},
                    {self.special_discount_account, line_a.account_id},
                )

                # Give line B a no-FP privilege while line A keeps FP, then
                # remove all and ensure full restore.
                self._apply_privilege(
                    invoice, privilege_id=self.privilege_without_tax.id,
                    apply_on="product", product_ids=[Command.set([self.product_b.id])],
                )
                self.assertEqual(line_b.l10n_ph_discount_privilege_id, self.privilege_without_tax)
                self.assertEqual(line_b.tax_ids, self.tax_sale_12)
                self.assertEqual(line_a.tax_ids, self.tax_sale_0_exempt_sc_pwd)

                self._create_wizard(invoice).action_remove_all()
                self.assertFalse(line_a.l10n_ph_discount_privilege_id)
                self.assertEqual(line_a.discount, 10.0)
                self.assertEqual(line_a.tax_ids, self.tax_sale_12)
                self.assertAlmostEqual(line_a.price_unit, price_unit, places=2)
                self.assertFalse(line_b.l10n_ph_discount_privilege_id)
                self.assertEqual(line_b.discount, 5.0)
                self.assertEqual(line_b.tax_ids, self.tax_sale_12)
                self.assertAlmostEqual(line_b.price_unit, 200.0, places=2)
                self.assertFalse(
                    invoice.line_ids.filtered(lambda line_item: line_item.display_type == "discount"),
                )

    # ============================================================
    #  Re-apply / Idempotency
    # ============================================================

    def test_wizard_mixed_privileged_and_unprivileged_lines_reapply(self):
        invoice = self.invoice
        self._apply_privilege(
            invoice,
            privilege_id=self.privilege.id,
            apply_on="product",
            product_ids=[Command.set([self.product_a.id])],
        )

        line_a, line_b = invoice.invoice_line_ids.sorted("sequence")
        self.assertTrue(line_a.l10n_ph_discount_privilege_id)
        self.assertFalse(line_b.l10n_ph_discount_privilege_id)

        self._apply_privilege(invoice, privilege_id=self.privilege.id, apply_on="all")

        line_a, line_b = invoice.invoice_line_ids.sorted("sequence")
        self.assertTrue(line_a.l10n_ph_discount_privilege_id)
        self.assertTrue(line_b.l10n_ph_discount_privilege_id)
        self.assertEqual(line_a.discount, 20.0)
        self.assertEqual(line_b.discount, 20.0)

    def test_apply_privilege_on_top_of_existing_privilege(self):
        """Applying a different FP-based privilege on a line that already
        carries one must re-map from the line's original, pre-any-privilege
        taxes (not the intermediate mapped ones) and re-route the discount
        allocation to the new privilege's account."""
        other_tax = self._create_tax("Other Exempt SC/PWD", 0.0)
        other_fpos = self.env["account.fiscal.position"].create({"name": "Other SC/PWD FP"})
        other_tax.write({"original_tax_ids": [Command.set([self.base_tax.id])]})
        other_fpos.write({"tax_ids": [Command.set([other_tax.id])]})
        other_account = self.special_discount_account.copy({"name": "Other Discount Account"})
        other_privilege = self._create_privilege(
            "Other FP Privilege",
            0.2,
            fiscal_position_id=other_fpos,
            account_id=other_account,
        )

        invoice = self._create_invoice_with_lines(
            ("Line A", self.product_a, 100.0, {"tax_ids": self.base_tax, "discount": 10.0}),
        )
        line = invoice.invoice_line_ids

        self._apply_privilege(invoice, privilege_id=self.privilege.id, apply_on="all")
        self.assertEqual(line.tax_ids, self.tax_sale_0_exempt_sc_pwd)
        self.assertEqual(line.l10n_ph_original_tax_ids, self.base_tax)
        self.assertEqual(line.discount, 20.0)
        self.assertEqual(line.l10n_ph_original_discount, 10.0)

        self._apply_privilege(invoice, privilege_id=other_privilege.id, apply_on="all")
        self.assertEqual(line.l10n_ph_discount_privilege_id, other_privilege)
        self.assertEqual(line.tax_ids, other_tax)
        self.assertEqual(line.l10n_ph_original_tax_ids, self.base_tax)
        self.assertEqual(line.discount, 20.0)
        # Original discount is still the pre-*any*-privilege value (10%), not
        # the intermediate 20% set by the first privilege.
        self.assertEqual(line.l10n_ph_original_discount, 10.0)

        # The allocation moved fully to the new privilege's account: no
        # stale entry is left pointing at the first privilege's account.
        discount_lines = invoice.line_ids.filtered(
            lambda line_item: line_item.display_type == "discount",
        )
        self.assertEqual(len(discount_lines), 2)
        self.assertEqual(
            {discount_line.account_id for discount_line in discount_lines},
            {line.account_id, other_account},
        )

    # ============================================================
    #  Preview Edge Cases
    # ============================================================

    def test_preview_reflects_applied_and_selected_privilege(self):
        invoice = self._single_line_invoice()
        wizard = self._create_wizard(invoice, privilege_id=self.privilege.id, apply_on="all")
        wizard.action_confirm()

        # Without a selected privilege, the preview shows the applied one.
        wizard = self._create_wizard(invoice)
        line_wiz = wizard.line_ids
        self.assertTrue(line_wiz.has_applied_discount_privilege)
        self.assertEqual(line_wiz.discount, 20.0)
        self.assertAlmostEqual(line_wiz.discount_amount, 20.0, places=2)

        # Selecting a different privilege projects its discount instead.
        priv30 = self._create_privilege("30% Priv", 0.3)
        wizard = self._create_wizard(invoice, privilege_id=priv30.id, apply_on="all")
        line_wiz = wizard.line_ids
        self.assertTrue(line_wiz.has_applied_discount_privilege)
        self.assertEqual(line_wiz.discount, 30.0)
        self.assertAlmostEqual(line_wiz.discount_amount, 30.0, places=2)

    # ============================================================
    #  Section / Note Lines
    # ============================================================

    def test_skip_discount_amounts_on_section_lines(self):
        invoice = self._create_invoice(
            invoice_line_ids=[
                Command.create({"name": "Section Title", "display_type": "line_section"}),
                self._prepare_invoice_line(name="Line A", product_id=self.product_a, price_unit=100.0),
                Command.create({"name": "Note", "display_type": "line_note"}),
            ],
        )
        self._apply_privilege(invoice, privilege_id=self.privilege.id, apply_on="all")

        section = invoice.line_ids.filtered(lambda line: line.display_type == "line_section")
        note = invoice.line_ids.filtered(lambda line: line.display_type == "line_note")
        product_line = invoice.invoice_line_ids.filtered(lambda line: line.display_type == "product")

        self.assertEqual(section.l10n_ph_special_discount_amount, 0.0)
        self.assertEqual(section.l10n_ph_regular_discount_amount, 0.0)
        self.assertEqual(note.l10n_ph_special_discount_amount, 0.0)
        self.assertEqual(note.l10n_ph_regular_discount_amount, 0.0)
        self.assertAlmostEqual(product_line.l10n_ph_special_discount_amount, 20.0, places=2)

    # ============================================================
    #  Quantity / Credit Notes / Copy
    # ============================================================

    def test_apply_with_quantity_greater_than_one(self):
        invoice = self.invoice
        line = invoice.invoice_line_ids[0]
        line.quantity = 3.0
        self._apply_privilege(invoice, privilege_id=self.privilege.id, apply_on="all")

        self.assertAlmostEqual(line.l10n_ph_special_discount_amount, 60.0)
        self.assertAlmostEqual(line.price_subtotal, 240.0)

    def test_apply_on_credit_note(self):
        credit_note = self._create_invoice_with_lines(
            ("Refund Line", self.product_a, 100.0),
            move_type="out_refund",
        )
        self._apply_privilege(
            credit_note, privilege_id=self.privilege.id, apply_on="all",
        )

        line = credit_note.invoice_line_ids
        self.assertEqual(line.l10n_ph_discount_privilege_id, self.privilege)
        self.assertEqual(line.discount, 20.0)
        self.assertEqual(line.tax_ids, self.tax_sale_0_exempt_sc_pwd)
        self.assertAlmostEqual(line.l10n_ph_special_discount_amount, 20.0)

    def test_copy_invoice_copies_privilege(self):
        invoice = self._single_line_invoice()
        self._apply_privilege(invoice, privilege_id=self.privilege.id, apply_on="all")
        self.assertTrue(invoice.invoice_line_ids.l10n_ph_discount_privilege_id)
        orig_line = invoice.invoice_line_ids

        copied = invoice.copy()
        line = copied.invoice_line_ids
        self.assertEqual(line.l10n_ph_discount_privilege_id, orig_line.l10n_ph_discount_privilege_id)
        self.assertEqual(line.l10n_ph_original_discount, orig_line.l10n_ph_original_discount)

        remove_wizard = self._create_wizard(copied)
        remove_wizard.action_remove_all()
        self.assertFalse(line.l10n_ph_discount_privilege_id)
        self.assertEqual(line.discount, orig_line.l10n_ph_original_discount)

    # ============================================================
    #  100 % Discount
    # ============================================================

    def test_apply_full_discount_100_percent(self):
        full = self._create_privilege("Full 100%", 1.0, discount_type="special")

        # Tax-excluded: discount base includes VAT (112) in preview.
        invoice = self._create_invoice_with_lines(
            ("Line A", self.product_a, 100.0),
        )
        wizard = self._create_wizard(invoice, privilege_id=full.id, apply_on="all")
        self.assertEqual(wizard.line_ids.discount, 100.0)
        self.assertAlmostEqual(wizard.line_ids.discount_amount, 112.0, places=2)

        wizard.action_confirm()
        line = invoice.invoice_line_ids
        self.assertEqual(line.discount, 100.0)
        self.assertAlmostEqual(line.price_subtotal, 0.0)
        self.assertAlmostEqual(line.l10n_ph_special_discount_amount, 112.0)
        self._assert_discount_allocation(invoice, line, 112.0)

        # Back-calculation at 100% keeps tax-included/tax-excluded bases.
        for tax, expected_amount in ((self.tax_incl, 500.0), (self.base_tax, 560.0)):
            with self.subTest(tax=tax.name):
                invoice = self._create_invoice_with_lines(
                    ("Line A", self.product_a, 500.0, {"tax_ids": tax}),
                )
                wizard = self._create_wizard(invoice, privilege_id=full.id, apply_on="all")
                wizard.action_confirm()
                line = invoice.invoice_line_ids
                self.assertEqual(line.discount, 100.0)
                self.assertAlmostEqual(line.price_subtotal, 0.0)
                self.assertAlmostEqual(
                    line.l10n_ph_special_discount_amount,
                    expected_amount,
                    places=2,
                )

    # ============================================================
    #  Discount Allocation Entries
    # ============================================================

    def test_apply_creates_discount_allocation_entries(self):
        invoice = self._single_line_invoice()
        self._apply_privilege(invoice, privilege_id=self.privilege.id, apply_on="all")
        self._assert_discount_allocation(invoice, invoice.invoice_line_ids, 20.0)

    def test_apply_privilege_clears_regular_discount(self):
        regular_discount_account = self.company_data["default_account_revenue"].copy(
            {"name": "Regular Discount Allocation Account"},
        )
        self.company_data["company"].account_discount_expense_allocation_id = regular_discount_account
        self.addCleanup(
            lambda: self.company_data["company"].write(
                {"account_discount_expense_allocation_id": False},
            ),
        )

        invoice = self._single_line_invoice()
        invoice.invoice_line_ids.discount = 10.0
        self._apply_privilege(
            invoice,
            privilege_id=self.privilege_without_tax.id,
            apply_on="all",
        )

        line = invoice.invoice_line_ids
        self.assertEqual(line.discount, 20.0)
        self.assertAlmostEqual(line.l10n_ph_regular_discount_amount, 0.0)
        self.assertAlmostEqual(line.l10n_ph_special_discount_amount, 22.4)
        self.assertAlmostEqual(line.price_subtotal, 80.0)
        self.assertAlmostEqual(line.price_total, 89.6)
        self._assert_discount_allocation(invoice, line, 22.4)

    # ============================================================
    #  Multi-Company / Access / Security
    # ============================================================

    def test_discount_privilege_records_are_hidden_outside_ph_company(self):
        other_company = self.env["res.company"].create(
            {"name": "Non-PH Company", "country_id": self.env.ref("base.us").id},
        )
        privilege = self._create_privilege("PH Only", 0.1)
        self.assertTrue(
            self.env["l10n_ph.discount.privilege"].search([("id", "=", privilege.id)]),
        )
        self.assertFalse(
            self.env["l10n_ph.discount.privilege"]
            .with_context(allowed_company_ids=other_company.ids)
            .search([("id", "=", privilege.id)]),
        )

    def test_invoicing_user_can_apply_but_not_configure_privileges(self):
        invoice_user = self.env["res.users"].create(
            {
                "name": "Invoice User",
                "login": "invoice.user@example.com",
                "email": "invoice.user@example.com",
                "company_id": self.company_data["company"].id,
                "company_ids": [Command.set(self.company_data["company"].ids)],
                "group_ids": [
                    Command.link(self.env.ref("account.group_account_invoice").id),
                ],
            },
        )
        readonly_user = self.env["res.users"].create(
            {
                "name": "Readonly User",
                "login": "readonly.user@example.com",
                "email": "readonly.user@example.com",
                "company_id": self.company_data["company"].id,
                "company_ids": [Command.set(self.company_data["company"].ids)],
                "group_ids": [
                    Command.link(self.env.ref("account.group_account_readonly").id),
                ],
            },
        )

        invoice = self.invoice
        wizard = (
            self.env["l10n_ph.discount.privilege.wizard"]
            .with_user(invoice_user)
            .with_context(
                active_id=invoice.id,
                active_ids=[invoice.id],
                active_model="account.move",
            )
            .create({"move_id": invoice.id})
        )
        self.assertEqual(wizard.line_ids.invoice_line_id, invoice.invoice_line_ids)

        # Invoicing users can apply via wizard but cannot configure privileges.
        with self.assertRaises(AccessError):
            self.env["l10n_ph.discount.privilege"].with_user(invoice_user).create(
                {
                    "name": "Invoice User Creates",
                    "discount_amount": 0.1,
                    "account_id": self.special_discount_account.id,
                    "company_id": self.company_data["company"].id,
                },
            )

        with self.assertRaises(AccessError):
            self.env["l10n_ph.discount.privilege"].with_user(readonly_user).create(
                {
                    "name": "Should Not Create",
                    "discount_amount": 0.1,
                    "account_id": self.special_discount_account.id,
                    "company_id": self.company_data["company"].id,
                },
            )

    def test_wizard_rejects_privilege_from_other_company(self):
        company_b = self.env["res.company"].create(
            {"name": "Company B", "country_id": self.env.ref("base.ph").id},
        )
        company_b.partner_id.l10n_ph_entity_type = "corporation"
        account_b = self.env["account.account"].create(
            {
                "code": "DISC-B",
                "name": "Discount B",
                "account_type": "income",
                "company_ids": [Command.set(company_b.ids)],
            },
        )
        priv_b = self._create_privilege(
            "Priv B",
            0.2,
            account_id=account_b,
            company_id=company_b.id,
        )

        invoice = self.invoice
        wizard = self._create_wizard(invoice)

        # The field-level company check rejects the other-company privilege.
        with self.assertRaises(UserError):
            wizard.privilege_id = priv_b

    # ============================================================
    #  Onchange Behavior
    # ============================================================

    def test_onchange_privilege_sets_category_scope(self):
        # If categories overlap invoice lines, onchange prefills category scope.
        invoice = self.invoice
        wizard = self._create_wizard(invoice)
        wizard.privilege_id = self.privilege_with_categories
        wizard._onchange_privilege_id()
        self.assertEqual(wizard.apply_on, "product_category")
        self.assertEqual(wizard.category_ids, self.category_a)

        # If categories are absent from invoice lines, scope stays unchanged.
        cat_x = self.env["product.category"].create({"name": "Cat X"})
        priv = self._create_privilege(
            "Cat X Only",
            0.15,
            applied_to_category_ids=[Command.set(cat_x.ids)],
        )

        wizard = self._create_wizard(invoice)
        wizard.privilege_id = priv
        wizard._onchange_privilege_id()
        self.assertEqual(wizard.apply_on, "all")
        self.assertFalse(wizard.category_ids)

    def test_privilege_category_restriction_preview_and_apply(self):
        # Category restriction must match preview and confirmation.
        invoice = self.invoice
        wizard = self._create_wizard(
            invoice,
            privilege_id=self.privilege_with_categories.id,
            apply_on="all",
        )

        line_a_wiz, line_b_wiz = wizard.line_ids.sorted("id")
        self.assertTrue(line_a_wiz.has_discount_privilege)
        self.assertEqual(line_a_wiz.discount, 20.0)
        self.assertAlmostEqual(line_a_wiz.discount_amount, 20.0)
        self.assertFalse(line_b_wiz.has_discount_privilege)

        wizard.action_confirm()

        line_a, line_b = invoice.invoice_line_ids.sorted("sequence")
        self.assertEqual(line_a.l10n_ph_discount_privilege_id, self.privilege_with_categories)
        self.assertEqual(line_a.discount, 20.0)
        self.assertAlmostEqual(line_a.l10n_ph_special_discount_amount, 20.0)
        self.assertFalse(line_b.l10n_ph_discount_privilege_id)
        self.assertEqual(line_b.discount, 0.0)
        self.assertEqual(line_b.tax_ids, self.base_tax)

    def test_confirm_with_privilege_matching_no_line_raises_error(self):
        # If no line matches the privilege categories, confirmation must error.
        invoice = self._single_line_invoice()
        cat_x = self.env["product.category"].create({"name": "Cat X"})
        priv = self._create_privilege(
            "Cat X Only",
            0.15,
            applied_to_category_ids=[Command.set(cat_x.ids)],
        )
        wizard = self._create_wizard(invoice, privilege_id=priv.id, apply_on="all")
        with self.assertRaises(UserError):
            wizard.action_confirm()
        # Invoice remains unchanged.
        self.assertFalse(invoice.invoice_line_ids.l10n_ph_discount_privilege_id)
        self.assertEqual(invoice.invoice_line_ids.discount, 0.0)

    # ============================================================
    #  Document Field Validation
    # ============================================================

    def test_create_without_document_field_raises_error(self):
        with self.assertRaises(ValidationError):
            self.env["l10n_ph.discount.privilege.wizard"].create({"apply_on": "all"})

    # ============================================================
    #  Edge Cases — posted invoices, vendor bills, mixed basket
    # ============================================================

    def test_cannot_modify_on_posted_invoice(self):
        invoice = self.invoice
        wizard = self._create_wizard(invoice, privilege_id=self.privilege.id, apply_on="all")
        wizard.action_confirm()
        invoice.action_post()

        # Posted invoices reject both apply and remove actions.
        with self.assertRaises(UserError):
            wizard.action_confirm()
        with self.assertRaises(UserError):
            wizard.action_remove_all()

    def test_privilege_not_applied_on_vendor_bill(self):
        bill = self._create_invoice_with_lines(
            (
                "Vendor Line",
                self.product_a,
                100.0,
                {
                    "account_id": self.company_data["default_account_expense"].id,
                    "tax_ids": (),
                },
            ),
            move_type="in_invoice",
        )
        self.assertFalse(bill.l10n_ph_has_discount_privilege)

    def test_two_privileges_by_category_keep_both_discount_accounts(self):
        # Applying two different privileges on separate product categories
        # must keep both privilege accounts on the journal items: the
        # second apply must not clobber the first privilege's allocation.
        sc_account = self.special_discount_account
        pwd_account = self.special_discount_account.copy(
            {"name": "PWD Discount Account"},
        )
        pwd_privilege = self._create_privilege(
            "PWD Category B Privilege",
            0.2,
            fiscal_position_id=self.fpos_sc_pwd,
            account_id=pwd_account,
        )

        invoice = self._create_invoice_with_lines(
            ("Line A", self.product_a, 100.0),
            ("Line B", self.product_b, 4500.0),
        )
        line_a, line_b = invoice.invoice_line_ids.sorted("sequence")

        # SC on Category A, then PWD on Category B.
        self._apply_privilege(
            invoice,
            privilege_id=self.privilege.id,
            apply_on="product_category",
            category_ids=[Command.set(self.category_a.ids)],
        )

        self._apply_privilege(
            invoice,
            privilege_id=pwd_privilege.id,
            apply_on="product_category",
            category_ids=[Command.set(self.category_b.ids)],
        )

        self.assertEqual(line_a.l10n_ph_discount_privilege_id, self.privilege)
        self.assertEqual(line_b.l10n_ph_discount_privilege_id, pwd_privilege)

        discount_lines = invoice.line_ids.filtered(
            lambda line_item: line_item.display_type == "discount",
        )
        self.assertEqual(len(discount_lines), 3)
        self.assertEqual(
            {line_item.account_id for line_item in discount_lines},
            {line_a.account_id, sc_account, pwd_account},
        )
        self.assertAlmostEqual(
            next(
                line_item.amount_currency
                for line_item in discount_lines
                if line_item.account_id == pwd_account
            ),
            900.0,
        )

    def test_mixed_basket_multiple_privileges(self):
        pwd_privilege = self._create_privilege(
            "PWD 20%",
            0.2,
            fiscal_position_id=self.fpos_sc_pwd,
        )
        sc5_privilege = self._create_privilege(
            "SC 5% Special Discount",
            0.05,
            discount_type="special",
        )

        product_c = self.env["product.product"].create(
            {"name": "Product C", "list_price": 300.0},
        )
        product_d = self.env["product.product"].create(
            {"name": "Product D", "list_price": 150.0},
        )

        invoice = self._create_invoice_with_lines(
            ("Line A (SC 20%)", self.product_a, 1000.0),
            ("Line B (PWD 20%)", self.product_b, 2000.0),
            ("Line C (SC 5%)", product_c, 3000.0),
            ("Line D (none)", product_d, 4000.0),
        )

        lines = invoice.invoice_line_ids.sorted("sequence")
        line_a, line_b, line_c, line_d = lines

        self._apply_privilege(
            invoice,
            privilege_id=self.privilege.id,
            apply_on="product",
            product_ids=[Command.set([self.product_a.id])],
        )

        self._apply_privilege(
            invoice,
            privilege_id=pwd_privilege.id,
            apply_on="product",
            product_ids=[Command.set([self.product_b.id])],
        )

        self._apply_privilege(
            invoice,
            privilege_id=sc5_privilege.id,
            apply_on="product",
            product_ids=[Command.set([product_c.id])],
        )

        self.assertEqual(line_a.l10n_ph_discount_privilege_id, self.privilege)
        self.assertEqual(line_a.discount, 20.0)
        self.assertAlmostEqual(line_a.l10n_ph_special_discount_amount, 200.0, places=2)

        self.assertEqual(line_b.l10n_ph_discount_privilege_id, pwd_privilege)
        self.assertEqual(line_b.discount, 20.0)
        self.assertAlmostEqual(line_b.l10n_ph_special_discount_amount, 400.0, places=2)

        self.assertEqual(line_c.l10n_ph_discount_privilege_id, sc5_privilege)
        self.assertEqual(line_c.discount, 5.0)
        self.assertAlmostEqual(line_c.l10n_ph_special_discount_amount, 168.0, places=2)

        self.assertFalse(line_d.l10n_ph_discount_privilege_id)
        self.assertEqual(line_d.discount, 0.0)
        self.assertEqual(line_d.tax_ids, self.base_tax)
        self.assertAlmostEqual(line_d.l10n_ph_special_discount_amount, 0.0)

        self.assertAlmostEqual(invoice.amount_total, 10072.0, places=2)

    # ============================================================
    #  Helpers
    # ============================================================

    @classmethod
    def _create_tax(cls, name, amount, price_include_override=None):
        """Create a simple percentage sale tax."""
        return cls.env["account.tax"].create(
            {
                "name": name,
                "amount": amount,
                "type_tax_use": "sale",
                "price_include_override": price_include_override,
            },
        )

    @classmethod
    def _create_privilege(
        cls,
        name,
        discount_amount,
        *,
        discount_type="pwd",
        fiscal_position_id=None,
        account_id=None,
        company_id=None,
        applied_to_category_ids=None,
    ):
        """Create a discount privilege for the test company."""
        vals = {
            "name": name,
            "discount_amount": discount_amount,
            "discount_type": discount_type,
            "fiscal_position_id": fiscal_position_id.id
            if fiscal_position_id
            else False,
            "account_id": (account_id or cls.special_discount_account).id,
            "applied_to_category_ids": applied_to_category_ids,
        }
        if company_id:
            vals["company_id"] = company_id
        return cls.env["l10n_ph.discount.privilege"].sudo().create(vals)

    def _create_wizard(self, invoice, **vals):
        """Open the wizard on ``invoice`` like the button does, then apply ``vals``."""
        action = invoice.action_open_discount_privilege_wizard()
        wizard = self.env["l10n_ph.discount.privilege.wizard"].browse(action["res_id"])
        if vals:
            wizard.write(vals)
        return wizard

    def _apply_privilege(self, invoice, **vals):
        """Open the wizard, apply ``vals`` and confirm; returns the wizard."""
        wizard = self._create_wizard(invoice, **vals)
        wizard.action_confirm()
        return wizard

    @classmethod
    def _create_invoice_with_lines(cls, *lines, **kwargs):
        """Create an invoice from ``(name, product, price_unit[, line_vals])`` specs."""
        invoice_line_ids = []
        for line in lines:
            name, product, price_unit = line[:3]
            line_values = line[3] if len(line) > 3 else {}
            invoice_line_ids.append(
                cls._prepare_invoice_line(
                    name=name,
                    product_id=product,
                    price_unit=price_unit,
                    **line_values,
                ),
            )
        return cls._create_invoice(invoice_line_ids=invoice_line_ids, **kwargs)

    def _single_line_invoice(self):
        """Return the shared invoice with only the first line kept."""
        invoice = self.invoice
        invoice.invoice_line_ids.sorted("sequence")[1:].unlink()
        return invoice

    def _assert_discount_allocation(self, invoice, line, amount):
        """Assert the discount is split between the line and privilege accounts."""
        discount_lines = invoice.line_ids.filtered(
            lambda line_item: line_item.display_type == "discount",
        ).sorted("amount_currency")
        self.assertRecordValues(
            discount_lines,
            [
                {"account_id": line.account_id.id, "amount_currency": -amount},
                {
                    "account_id": self.special_discount_account.id,
                    "amount_currency": amount,
                },
            ],
        )
