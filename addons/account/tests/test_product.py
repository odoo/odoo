from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged
from odoo.tests.common import new_test_user

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "post_install_l10n", "-at_install")
class TestProduct(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.internal_user = new_test_user(
            cls.env,
            login="internal_user",
            groups="base.group_user",
        )
        cls.account_manager_user = new_test_user(
            cls.env,
            login="account_manager_user",
            groups="account.group_account_manager",
        )
        cls.other_company = cls.setup_other_company()["company"]
        cls.both_companies = cls.env.company | cls.other_company

    def test_internal_user_can_read_product_with_tax_and_tags(self):
        tax_line_tag = self.env["account.account.tag"].create(
            {
                "name": "Tax tag",
                "applicability": "taxes",
            }
        )
        self.product_a.taxes_id.repartition_line_ids.tag_ids = tax_line_tag
        self.env.invalidate_all()
        with Form(self.product_a.with_user(self.internal_user)) as form_a:
            self.assertTrue(form_a.tax_string)

    def test_multi_company_product_tax(self):
        product_without_company = (
            self.env["product.template"]
            .with_context(allowed_company_ids=self.env.company.ids)
            .create(
                {
                    "name": "Product Without a Company",
                }
            )
        )
        product_with_company = (
            self.env["product.template"]
            .with_context(allowed_company_ids=self.env.company.ids)
            .create(
                {
                    "name": "Product With a Company",
                    "company_id": self.company_data["company"].id,
                }
            )
        )
        companies = self.env["res.company"].sudo().search([])
        self.assertRecordValues(
            product_without_company.sudo(),
            [
                {
                    "taxes_id": companies.account_sale_tax_id.ids,
                    "supplier_taxes_id": companies.account_purchase_tax_id.ids,
                }
            ],
        )
        self.assertRecordValues(
            product_with_company.sudo(),
            [
                {
                    "taxes_id": self.company_data["company"].account_sale_tax_id.ids,
                    "supplier_taxes_id": self.company_data[
                        "company"
                    ].account_purchase_tax_id.ids,
                }
            ],
        )

    def test_product_tax_with_company_and_branch(self):
        parent_company = self.env.company
        self.env["res.company"].create(
            {
                "name": "Branch Company",
                "parent_id": parent_company.id,
                "account_sale_tax_id": parent_company.account_sale_tax_id.id,
            }
        )

        tax_new = self.env["account.tax"].create(
            {
                "name": "tax_new",
                "amount_type": "percent",
                "amount": 21.0,
                "type_tax_use": "sale",
            }
        )

        product = (
            self.env["product.template"]
            .with_context(allowed_company_ids=[parent_company.id])
            .create(
                {
                    "name": "Product with new Tax",
                    "taxes_id": tax_new.ids,
                }
            )
        )

        self.assertEqual(
            product.taxes_id,
            tax_new,
            "The branch company default tax shouldn't be set if we set a different tax on the product from the parent company.",
        )

    def test_get_list_price_price_included_tax_subcent(self):
        tax_incl = self.env["account.tax"].create(
            {
                "name": "16% included",
                "amount": 16.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "price_include_override": "tax_included",
            }
        )
        product = self.env["product.template"].create(
            {"name": "Sub-cent priced", "taxes_id": tax_incl.ids}
        )
        currency = product.currency_id
        for price, expected in [(1234.567, 1234.57), (100.005, 100.01), (100.0, 100.0)]:
            self.assertEqual(
                currency.compare_amounts(product._get_list_price(price), expected),
                0,
                f"_get_list_price({price}) with a price-included tax should round"
                " to the input price",
            )

    def test_get_list_price_price_excluded_tax(self):
        tax_excl = self.env["account.tax"].create(
            {
                "name": "21% excluded",
                "amount": 21.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "price_include_override": "tax_excluded",
            }
        )
        product = self.env["product.template"].create(
            {"name": "Excl priced", "taxes_id": tax_excl.ids}
        )
        self.assertEqual(
            product.currency_id.compare_amounts(product._get_list_price(121.0), 100.0),
            0,
        )

    def test_imported_product_by_identifiers(self):
        Product = self.env["product.product"]
        product = Product.create(
            {
                "name": "ZZ Retrieval Probe",
                "default_code": "RET-PROBE-001",
                "barcode": "0000000012345",
            }
        )
        self.assertEqual(
            Product._get_imported_product(barcode="0000000012345"), product
        )
        self.assertEqual(
            Product._get_imported_product(default_code="RET-PROBE-001"), product
        )
        self.assertEqual(
            Product._get_imported_product(name="ZZ Retrieval Probe"), product
        )
        self.assertFalse(Product._get_imported_product(barcode="NO-SUCH-BARCODE"))

    def test_import_product_search_plan_priority_collision(self):
        Product = self.env["product.product"]
        product = Product.create({"name": "ZZ Collision Probe"})
        original_plan = Product._get_import_product_search_plan

        def colliding_plan(self):
            return original_plan() + [(5, self._get_import_criteria_from_default_code)]

        with patch.object(
            type(Product), "_get_import_product_search_plan", colliding_plan
        ):
            self.assertEqual(
                Product._get_imported_product(name="ZZ Collision Probe"), product
            )

    def test_imported_product_extra_domain(self):
        Product = self.env["product.product"]
        product = Product.create(
            {"name": "ZZ Extra Domain Probe", "default_code": "RET-EXTRA-1"}
        )
        self.assertFalse(
            Product._get_imported_product(
                default_code="RET-EXTRA-1", extra_domain=[("id", "=", -1)]
            ),
            "extra_domain excluding the match must suppress it",
        )
        self.assertEqual(
            Product._get_imported_product(
                default_code="RET-EXTRA-1", extra_domain=[("id", "=", product.id)]
            ),
            product,
        )

    def _set_name_similarity_threshold(self, value):
        parameter = self.env["ir.config_parameter"].sudo()
        previous = parameter.get_param("account.product_name_similarity_threshold")
        parameter.set_param("account.product_name_similarity_threshold", value)
        self.addCleanup(
            parameter.set_param,
            "account.product_name_similarity_threshold",
            previous,
        )

    def test_imported_product_by_name_returns_best_match(self):
        Product = self.env["product.product"]
        Product.create({"name": "ZZ Widget X"})
        best = Product.create({"name": "ZZ Widgets"})
        self._set_name_similarity_threshold("0.5")
        self.assertEqual(Product._get_imported_product(name="ZZ Widget"), best)

    def test_get_product_accounts_requires_single_record(self):
        products = self.product_a + self.product_b
        with self.assertRaises(ValueError):
            products._get_product_accounts()

    def test_import_product_classification_domain_inert_without_codes(self):
        Product = self.env["product.product"]
        self.assertEqual(
            Product._get_domain_import_product_classification({"name": "x"}),
            ([], []),
        )

    def test_import_product_classification_specs_are_contributed(self):
        Product = self.env["product.product"]
        for spec in Product._get_import_product_classification_specs():
            self.assertIn(
                spec["field"],
                Product._fields,
                "a module contributing a classification spec must be the module"
                " that defines the field",
            )
            self.assertIn(
                spec["comodel"],
                self.env,
                "and the comodel that goes with it",
            )

    def _product_carrying_two_companies_taxes(self):
        return (
            self.env["product.template"]
            .with_context(allowed_company_ids=self.both_companies.ids)
            .with_company(self.env.company)
            .create({"name": "ZZ Two Company Priced", "list_price": 100.0})
        )

    def test_list_price_control_foreign_taxes_are_linked(self):
        product = self._product_carrying_two_companies_taxes()
        self.assertIn(
            self.other_company,
            product.sudo().taxes_id.company_ids,
            "control: create() links the other companies' default sale taxes, so"
            " every reader of taxes_id has to filter by company",
        )

    def test_list_price_control_record_rule_hides_foreign_taxes(self):
        product = self._product_carrying_two_companies_taxes()
        self.assertEqual(
            product.with_context(
                allowed_company_ids=self.env.company.ids
            ).taxes_id.company_ids,
            self.env.company,
            "control: with a single company active the account.tax record rule"
            " already filters them out - which is what used to hide the defect",
        )

    def _gross_price_of_hundred(self, product):
        taxes = product.sudo().taxes_id._filter_taxes_by_company(self.env.company)
        self.assertTrue(taxes, "control: the active company needs a default sale tax")
        return taxes.compute_all(100.0, product.currency_id, product=product)[
            "total_included"
        ]

    def test_list_price_strips_only_the_active_companys_taxes(self):
        product = self._product_carrying_two_companies_taxes()
        widened = product.with_context(allowed_company_ids=self.both_companies.ids)
        self.assertIn(
            self.other_company,
            widened.taxes_id.company_ids,
            "control: with both companies active nothing filters the foreign tax",
        )
        self.assertEqual(
            product.currency_id.compare_amounts(
                widened._get_list_price(self._gross_price_of_hundred(product)), 100.0
            ),
            0,
        )

    def test_list_price_strips_only_the_active_companys_taxes_under_sudo(self):
        product = self._product_carrying_two_companies_taxes()
        gross = self._gross_price_of_hundred(product)
        self.env.invalidate_all()
        self.assertIn(
            self.other_company,
            product.sudo().taxes_id.company_ids,
            "control: sudo bypasses the record rule that was masking this",
        )
        self.assertEqual(
            product.currency_id.compare_amounts(
                product.sudo()._get_list_price(gross), 100.0
            ),
            0,
        )

    def _product_of_the_other_company_without_category_accounts(self):
        category = self.env["product.category"].create({"name": "ZZ No Accounts"})
        for company in self.both_companies:
            category.with_company(company).property_account_income_categ_id = False
        return (
            self.env["product.template"]
            .with_context(allowed_company_ids=self.both_companies.ids)
            .with_company(self.env.company)
            .create(
                {
                    "name": "ZZ Foreign Product",
                    "company_id": self.other_company.id,
                    "categ_id": category.id,
                }
            )
        )

    def test_product_accounts_control_the_company_fallback_is_reachable(self):
        product = self._product_of_the_other_company_without_category_accounts()
        self.assertFalse(product.property_account_income_id)
        self.assertFalse(
            product._get_category_account("property_account_income_categ_id"),
            "control: emptying the account on the whole category ancestry is what"
            " makes the company-level fallback reachable at all",
        )
        self.assertTrue(product._get_product_accounts()["income"])

    def test_product_accounts_resolve_against_the_active_company(self):
        product = self._product_of_the_other_company_without_category_accounts()
        self.assertIn(
            self.env.company,
            product._get_product_accounts()["income"].company_ids,
            "the account lands on a journal item of env.company, so every"
            " fallback level has to resolve against env.company",
        )

    def test_category_account_walks_up_to_an_ancestor(self):
        Category = self.env["product.category"]
        root = Category.create({"name": "ZZ Root"})
        leaf = Category.create({"name": "ZZ Leaf", "parent_id": root.id})
        account = self.company_data["default_account_revenue"]
        root.property_account_income_categ_id = account
        leaf.property_account_income_categ_id = False
        product = self.env["product.template"].create(
            {"name": "ZZ Walk", "categ_id": leaf.id}
        )
        self.assertFalse(leaf.property_account_income_categ_id, "control")
        self.assertEqual(
            product._get_category_account("property_account_income_categ_id"),
            account,
        )

    def test_category_account_of_an_untouched_category_is_the_company_default(self):
        category = self.env["product.category"].create({"name": "ZZ Untouched"})
        product = self.env["product.template"].create(
            {"name": "ZZ Untouched Product", "categ_id": category.id}
        )
        self.assertEqual(
            product._get_category_account("property_account_income_categ_id"),
            self.env.company.income_account_id,
            "res_company._set_category_defaults mirrors income_account_id into"
            " ir.default, so an untouched category already answers with it",
        )

    def test_product_accounts_are_mapped_by_the_fiscal_position(self):
        fiscal_position = self.env["account.fiscal.position"].create(
            {
                "name": "ZZ Mapping",
                "account_ids": [
                    (
                        0,
                        0,
                        {
                            "account_src_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "account_dest_id": self.company_data[
                                "default_account_expense"
                            ].id,
                        },
                    )
                ],
            }
        )
        product = self.env["product.template"].create(
            {
                "name": "ZZ Mapped",
                "property_account_income_id": self.company_data[
                    "default_account_revenue"
                ].id,
            }
        )
        self.assertEqual(
            product._get_product_accounts()["income"],
            self.company_data["default_account_revenue"],
        )
        self.assertEqual(
            product._get_product_accounts(fiscal_pos=fiscal_position)["income"],
            self.company_data["default_account_expense"],
        )

    def _post_invoice_for(self, product, uom):
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-01-01",
                "date": "2026-01-01",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.product_variant_id.id,
                            "quantity": 3,
                            "price_unit": 10,
                            "product_uom_id": uom.id,
                        },
                    )
                ],
            }
        )
        move.action_post()
        return move

    def test_uom_change_is_blocked_after_an_invoice_in_the_same_uom(self):
        unit = self.env.ref("uom.product_uom_unit")
        product = self.env["product.template"].create(
            {"name": "ZZ Uom Same", "uom_id": unit.id}
        )
        self._post_invoice_for(product, unit)
        with self.assertRaises(ValidationError):
            product.uom_id = self.env.ref("uom.product_uom_kgm")
            self.env.flush_all()

    def test_uom_change_is_blocked_after_an_invoice_in_another_uom(self):
        unit = self.env.ref("uom.product_uom_unit")
        dozen = self.env.ref("uom.product_uom_dozen")
        product = self.env["product.template"].create(
            {"name": "ZZ Uom Other", "uom_id": unit.id}
        )
        line = self._post_invoice_for(product, dozen).invoice_line_ids
        before = line.product_uom_id._get_quantity_in_unit(
            line.quantity, line.product_id.uom_id
        )
        with self.assertRaises(
            ValidationError,
            msg="whichever unit the entry used, the product's own unit is frozen"
            " once it has been posted",
        ):
            product.uom_id = dozen
            self.env.flush_all()
        self.assertEqual(
            before,
            line.product_uom_id._get_quantity_in_unit(
                line.quantity, line.product_id.uom_id
            ),
            "a posted quantity must keep the meaning it was posted with",
        )

    def test_uom_can_be_rewritten_to_the_same_value(self):
        unit = self.env.ref("uom.product_uom_unit")
        product = self.env["product.template"].create(
            {"name": "ZZ Uom Rewrite", "uom_id": unit.id}
        )
        self._post_invoice_for(product, unit)
        product.write({"uom_id": unit.id})
        self.env.flush_all()
        self.assertEqual(product.uom_id, unit)

    def test_uom_change_is_allowed_while_the_entry_is_a_draft(self):
        unit = self.env.ref("uom.product_uom_unit")
        kilogram = self.env.ref("uom.product_uom_kgm")
        product = self.env["product.template"].create(
            {"name": "ZZ Uom Draft", "uom_id": unit.id}
        )
        self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-01-01",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.product_variant_id.id,
                            "quantity": 1,
                            "price_unit": 10,
                        },
                    )
                ],
            }
        )
        product.uom_id = kilogram
        self.env.flush_all()
        self.assertEqual(product.uom_id, kilogram)

    def test_a_combo_product_carries_no_taxes_however_it_is_created(self):
        base = self.env["product.template"].create({"name": "ZZ Combo Item"})
        combo = self.env["product.combo"].create(
            {
                "name": "ZZ Combo",
                "combo_item_ids": [(0, 0, {"product_id": base.product_variant_id.id})],
            }
        )
        product = (
            self.env["product.template"]
            .with_context(allowed_company_ids=self.both_companies.ids)
            .create(
                {
                    "name": "ZZ Combo Product",
                    "type": "combo",
                    "combo_ids": [(6, 0, combo.ids)],
                }
            )
        )
        self.assertFalse(product.sudo().taxes_id)
        self.assertFalse(product.sudo().supplier_taxes_id)

    def test_turning_a_product_into_a_combo_drops_its_taxes(self):
        product = self.env["product.template"].create({"name": "ZZ Becomes Combo"})
        self.assertTrue(product.taxes_id, "control: it starts with the default tax")
        base = self.env["product.template"].create({"name": "ZZ Combo Item 2"})
        combo = self.env["product.combo"].create(
            {
                "name": "ZZ Combo 2",
                "combo_item_ids": [(0, 0, {"product_id": base.product_variant_id.id})],
            }
        )
        product.write({"type": "combo", "combo_ids": [(6, 0, combo.ids)]})
        self.assertFalse(product.sudo().taxes_id)

    def test_import_lookup_finds_a_name_that_ilike_cannot(self):
        Product = self.env["product.product"]
        stored = Product.create({"name": "ZZ Widgets Deluxe"})
        self._set_name_similarity_threshold("0.9")
        self.assertEqual(
            Product._get_imported_product(name="ZZ Widgets Deluxe"),
            stored,
            "control: the exact name resolves",
        )
        self.assertEqual(
            Product._get_imported_product(name="ZZ Widget Deluxe"),
            stored,
            "SequenceMatcher scores this 0.97, above the threshold; a `name ilike`"
            " prefilter would never offer it as a candidate",
        )

    def test_import_lookup_still_rejects_a_name_below_the_threshold(self):
        Product = self.env["product.product"]
        Product.create({"name": "ZZ Widgets Deluxe Extended Warranty Pack"})
        self._set_name_similarity_threshold("0.9")
        self.assertFalse(
            Product._get_imported_product(name="ZZ Widgets"),
            "recall got broader, the decision did not",
        )

    def test_import_lookup_of_the_same_name_does_not_search_again_per_line(self):
        Product = self.env["product.product"]
        Product.create([{"name": f"ZZ Repeat {index}"} for index in range(20)])
        self.env.flush_all()
        model = type(Product)
        real_search = model.search
        searches = []

        def counting_search(records, domain, **kwargs):
            if records._name == "product.product":
                searches.append(domain)
            return real_search(records, domain, **kwargs)

        with patch.object(model, "search", counting_search):
            Product._get_imported_product(name="ZZ Repeat")
            first = len(searches)
            for _ in range(4):
                Product._get_imported_product(name="ZZ Repeat")
        self.assertTrue(first, "control: the first lookup reaches the database")
        self.assertLessEqual(
            len(searches),
            first * 5,
            "a repeated lookup must not cost more than the first one",
        )
