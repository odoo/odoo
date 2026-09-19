from freezegun import freeze_time
from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user, tagged
from odoo.tools import file_open

from odoo.addons.account.models.res_partner import _ref_company_registry
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountPartner(AccountTestInvoicingCommon):
    @freeze_time("2023-05-31")
    def test_days_sales_outstanding(self):
        partner = self.env["res.partner"].create({"name": "MyCustomer"})
        self.assertEqual(partner.days_sales_outstanding, 0.0)
        move_1 = self.init_invoice(
            "out_invoice",
            partner,
            invoice_date="2023-01-01",
            amounts=[3000],
            taxes=self.tax_sale_a,
        )
        self.assertEqual(partner.days_sales_outstanding, 0.0)
        move_1.action_post()
        self.env.invalidate_all()
        self.assertEqual(partner.days_sales_outstanding, 150)
        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=move_1.ids
        ).create(
            {
                "amount": move_1.amount_total,
                "partner_id": partner.id,
                "payment_type": "inbound",
                "partner_type": "customer",
            }
        )._create_payments()
        self.env.invalidate_all()
        self.assertEqual(partner.days_sales_outstanding, 0.0)
        self.init_invoice(
            "out_invoice",
            partner,
            "2023-05-15",
            amounts=[1500],
            taxes=self.tax_sale_a,
            post=True,
        )
        self.env.invalidate_all()
        self.assertEqual(partner.days_sales_outstanding, 50)

    def test_credit_search_matches_credit_on_archived_account(self):
        partner = self.env["res.partner"].create({"name": "ArchivedAcctDebtor"})
        move = self.init_invoice(
            "out_invoice", partner, invoice_date="2023-01-01", amounts=[1000], post=True
        )
        self.env.invalidate_all()
        self.assertGreater(partner.credit, 0)
        self.assertIn(partner, self.env["res.partner"].search([("credit", ">", 0)]))

        receivable_account = move.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        ).account_id
        receivable_account.active = False
        self.env.invalidate_all()

        self.assertGreater(
            partner.credit, 0, "an archived account does not erase the debt"
        )
        self.assertIn(
            partner,
            self.env["res.partner"].search([("credit", ">", 0)]),
            "the credit filter must agree with the displayed Total Receivable",
        )

    def test_move_counts_roll_up_to_parent(self):
        parent = self.env["res.partner"].create({"name": "RollupParent"})
        child = self.env["res.partner"].create(
            {"name": "RollupChild", "parent_id": parent.id}
        )
        self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "invoice_date": "2023-01-01",
                "partner_id": child.id,
                "invoice_line_ids": [
                    Command.create({"name": "l", "price_unit": 700.0})
                ],
            }
        ).action_post()
        self.env.invalidate_all()

        self.assertEqual(child.account_move_count, 1)
        self.assertEqual(
            parent.account_move_count,
            1,
            "the child's moves roll up to the parent",
        )
        self.assertEqual(child.customer_invoice_count, 1)
        self.assertEqual(parent.customer_invoice_count, 1)

    def test_partner_rank_increases_on_post(self):
        self.env["account.move"].create(
            [
                {
                    "move_type": "out_invoice",
                    "date": "2017-01-01",
                    "invoice_date": "2017-01-01",
                    "partner_id": self.partner_a.id,
                    "invoice_line_ids": [(0, 0, {"name": "aaaa", "price_unit": 100.0})],
                },
                {
                    "move_type": "in_invoice",
                    "date": "2017-01-01",
                    "invoice_date": "2017-01-01",
                    "partner_id": self.partner_a.id,
                    "invoice_line_ids": [(0, 0, {"name": "aaaa", "price_unit": 100.0})],
                },
            ]
        ).action_post()

        with self.enter_registry_test_mode():
            self.env.cr.postcommit.run()
        self.assertEqual(self.partner_a.supplier_rank, 1)
        self.assertEqual(self.partner_a.customer_rank, 1)

        self.env["account.move"].create(
            [
                {
                    "move_type": "out_invoice",
                    "date": "2017-01-02",
                    "invoice_date": "2017-01-02",
                    "partner_id": self.partner_a.id,
                    "invoice_line_ids": [(0, 0, {"name": "aaaa", "price_unit": 100.0})],
                },
            ]
        ).action_post()
        with self.enter_registry_test_mode():
            self.env.cr.postcommit.run()
        self.assertEqual(self.partner_a.customer_rank, 2)

    def test_manually_write_partner_id(self):
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "invoice_date": "2025-04-29",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "quantity": 1,
                            "price_unit": 500.0,
                            "tax_ids": [Command.link(self.tax_sale_a.id)],
                        }
                    )
                ],
            }
        )
        move.action_post()
        reversal = move._reverse_moves(cancel=True)

        receivable_lines = (move + reversal).line_ids.filtered(
            lambda l: l.display_type == "payment_term"
        )

        move.company_id.account_config_id.fiscalyear_lock_date = "9999-12-31"
        move.company_id.account_config_id.tax_lock_date = "9999-12-31"

        self.assertEqual(move.commercial_partner_id, self.partner_a)
        self.assertEqual(receivable_lines.mapped("reconciled"), [True, True])

        self.partner_a.parent_id = self.partner_b

        self.assertEqual(move.commercial_partner_id, self.partner_b)
        self.assertTrue(
            all(line.partner_id == self.partner_b for line in move.line_ids),
            "All move lines should be reassigned to the new commercial partner.",
        )
        self.assertEqual(receivable_lines.mapped("reconciled"), [True, True])

    def test_manually_write_partner_id_different_vat(self):
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "invoice_date": "2025-04-29",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "quantity": 1,
                            "price_unit": 500.0,
                        }
                    )
                ],
            }
        )
        move.action_post()
        self.partner_a.vat = "SOMETHING"
        self.partner_b.vat = "DIFFERENT"
        with self.assertRaisesRegex(UserError, "different Tax ID"):
            self.partner_a.parent_id = self.partner_b

    def test_manually_write_partner_id_empty_string_vs_False(self):
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "invoice_date": "2025-04-29",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "quantity": 1,
                            "price_unit": 500.0,
                        }
                    )
                ],
            }
        )
        move.action_post()
        self.partner_a.vat = ""
        self.partner_b.vat = False

        self.partner_a.parent_id = self.partner_b

    def test_res_partner_bank(self):
        self.env.user.group_ids -= self.env.ref("base.group_system")
        self.env.user.group_ids += self.env.ref("base.group_partner_manager")
        self.env.user.group_ids += self.env.ref("account.group_validate_bank_account")
        partner = self.env["res.partner"].create({"name": "MyCustomer"})
        account = self.env["res.partner.bank"].create(
            {
                "acc_number": "123456789",
                "partner_id": partner.id,
            }
        )
        account.allow_out_payment = True

        with self.assertRaisesRegex(UserError, "has been trusted"), self.cr.savepoint():
            account.write({"acc_number": "1234567890999"})
        with self.assertRaisesRegex(UserError, "has been trusted"), self.cr.savepoint():
            account.write({"sanitized_acc_number": "1234567890999"})
        with self.assertRaisesRegex(UserError, "has been trusted"), self.cr.savepoint():
            account.write(
                {
                    "partner_id": self.env["res.partner"]
                    .create({"name": "MyCustomer 2"})
                    .id
                }
            )

        account.allow_out_payment = False
        account.write({"acc_number": "1234567890999000"})

        self.env.user.group_ids -= self.env.ref("account.group_validate_bank_account")
        with (
            self.assertRaisesRegex(UserError, "You do not have the rights to trust"),
            self.cr.savepoint(),
        ):
            account.write({"allow_out_payment": True})

    @freeze_time("2023-06-30")
    def test_days_sales_outstanding_never_negative(self):
        partner = self.env["res.partner"].create({"name": "NegDSO"})
        inv = self.init_invoice(
            "out_invoice", partner, invoice_date="2023-01-01", amounts=[5000], post=True
        )
        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=inv.ids
        ).create({"amount": inv.amount_total})._create_payments()
        self.init_invoice(
            "out_refund", partner, invoice_date="2023-02-01", amounts=[100], post=True
        )
        self.env.invalidate_all()
        self.assertLess(partner.credit, 0, "sanity: customer is in credit balance")
        self.assertGreaterEqual(
            partner.days_sales_outstanding,
            0.0,
            "DSO must stay non-negative even for a credit-balance customer",
        )

    def test_credit_search_ignores_partnerless_lines(self):
        partner = self.env["res.partner"].create({"name": "RealDebtor"})
        self.init_invoice(
            "out_invoice", partner, invoice_date="2023-01-01", amounts=[1000], post=True
        )
        recv = self.company_data["default_account_receivable"]
        rev = self.company_data["default_account_revenue"]
        misc = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2023-03-01",
                "line_ids": [
                    Command.create({"account_id": recv.id, "debit": 300, "credit": 0}),
                    Command.create({"account_id": rev.id, "debit": 0, "credit": 300}),
                ],
            }
        )
        misc.action_post()
        self.assertFalse(
            misc.line_ids.filtered(lambda l: l.account_id == recv).partner_id,
            "sanity: the receivable line really has no partner",
        )
        self.env.invalidate_all()

        Partner = self.env["res.partner"]
        self.assertIn(partner, Partner.search([("credit", ">", 0)]))
        for op, operand in ((">=", 0), ("=", 0), ("<=", 0)):
            self.assertTrue(
                Partner.search([("credit", op, operand)]),
                f"a partnerless line emptied out credit {op} {operand}",
            )

    def test_map_tax_account_singleton_contract(self):
        FP = self.env["account.fiscal.position"]
        tax = self.tax_sale_a
        acc = self.company_data["default_account_receivable"]

        self.assertEqual(FP.map_tax(tax), tax, "empty position leaves taxes unchanged")
        self.assertEqual(
            FP.map_account(acc), acc, "empty position leaves account as-is"
        )

        both = FP.create({"name": "FP a"}) + FP.create({"name": "FP b"})
        with self.assertRaises(ValueError):
            both.map_tax(tax)
        with self.assertRaises(ValueError):
            both.map_account(acc)

    def test_fiscal_country_codes_lands_in_the_misc_group(self):
        view = self.env["res.partner"].get_view(
            view_id=self.env.ref("account.view_partner_property_form").id,
            view_type="form",
        )
        arch = etree.fromstring(view["arch"])
        misc_group = arch.find(".//group[@name='misc']")
        self.assertIsNotNone(misc_group)
        self.assertIsNotNone(
            misc_group.find(".//field[@name='fiscal_country_codes']"),
            "fiscal_country_codes must be inside group[@name='misc']",
        )
        child_ids_field = arch.find(".//field[@name='child_ids']")
        if child_ids_field is not None:
            self.assertIsNone(
                child_ids_field.find(".//field[@name='fiscal_country_codes']"),
                "fiscal_country_codes must not be nested inside child_ids' own subview",
            )

    def test_credit_search_covers_partners_without_any_line(self):
        no_line = self.env["res.partner"].create({"name": "NoAccountingLine"})
        debtor = self.env["res.partner"].create({"name": "Debtor"})
        self.init_invoice(
            "out_invoice", debtor, invoice_date="2023-01-01", amounts=[900], post=True
        )
        self.env.invalidate_all()

        self.assertEqual(no_line.credit, 0.0, "sanity: the field displays 0.0")
        Partner = self.env["res.partner"]
        for op, operand, expected in (
            ("=", 0, True),
            (">=", 0, True),
            ("<=", 0, True),
            ("!=", 0, False),
            (">", 0, False),
        ):
            self.assertEqual(
                no_line in Partner.search([("credit", op, operand)]),
                expected,
                f"credit {op} {operand} disagrees with the displayed 0.0",
            )
        self.assertIn(debtor, Partner.search([("credit", "!=", 0)]))
        self.assertIn(debtor, Partner.search([("credit", "=", 900)]))
        self.assertNotIn(debtor, Partner.search([("credit", "=", 0)]))

    def test_credit_search_supports_the_orm_normalised_operators(self):
        Partner = self.env["res.partner"]
        for domain in (
            [("credit", "in", [0])],
            [("credit", "not in", [0])],
            [("debit", "=", 0)],
            [("debit", "!=", 0)],
            [("credit", "=", False)],
        ):
            Partner.search(domain)

    def test_days_sales_outstanding_is_group_restricted_like_credit(self):
        Partner = self.env["res.partner"]
        self.assertEqual(
            Partner._fields["days_sales_outstanding"].groups,
            Partner._fields["credit"].groups,
        )
        partner = Partner.create({"name": "DsoAccess"})
        salesperson = new_test_user(
            self.env, login="dso_salesperson", groups="base.group_user"
        )
        self.assertFalse(salesperson.has_group("account.group_account_invoice"))
        self.assertFalse(salesperson.has_group("account.group_account_readonly"))

        restricted = self.env(user=salesperson)
        restricted.invalidate_all()
        with self.assertRaises(AccessError) as caught:
            partner.with_env(restricted).days_sales_outstanding
        self.assertIn("days_sales_outstanding", str(caught.exception))

    def test_move_counts_are_scoped_to_the_active_company(self):
        other = self.setup_other_company()
        partner = self.env["res.partner"].create({"name": "MultiCoCustomer"})
        self.init_invoice(
            "out_invoice", partner, invoice_date="2023-01-01", amounts=[100], post=True
        )
        self.env["account.move"].with_company(other["company"]).create(
            [
                {
                    "move_type": "out_invoice",
                    "invoice_date": "2023-01-01",
                    "partner_id": partner.id,
                    "invoice_line_ids": [
                        Command.create({"name": "l", "price_unit": 500})
                    ],
                }
            ]
            * 2
        ).action_post()
        self.env.invalidate_all()

        here = partner.with_company(self.env.company).customer_invoice_count
        there = partner.with_company(other["company"]).customer_invoice_count
        self.assertEqual(here, 1)
        self.assertEqual(
            there, 2, "the count must follow the company, not the first read"
        )

    def test_move_counts_use_two_different_company_scopes(self):
        other = self.setup_other_company()
        accountant = new_test_user(
            self.env,
            login="two_scope_accountant",
            groups="base.group_user,account.group_account_user,base.group_multi_company",
        )
        accountant.company_ids = [
            Command.set([self.env.company.id, other["company"].id])
        ]
        accountant.company_id = self.env.company
        partner = self.env["res.partner"].create({"name": "TwoScopes"})
        self.init_invoice(
            "out_invoice", partner, invoice_date="2023-01-01", amounts=[100], post=True
        )
        for amount in (500, 700):
            self.env["account.move"].with_company(other["company"]).create(
                {
                    "move_type": "out_invoice",
                    "invoice_date": "2023-01-01",
                    "partner_id": partner.id,
                    "invoice_line_ids": [
                        Command.create({"name": "l", "price_unit": amount})
                    ],
                }
            ).action_post()
        self.env.flush_all()

        as_user = self.env(user=accountant)
        both = as_user(
            context=dict(
                as_user.context,
                allowed_company_ids=[self.env.company.id, other["company"].id],
            )
        )
        both.invalidate_all()
        visible = partner.with_env(both)
        self.assertEqual(
            visible.account_move_count, 3, "counts every company the user enabled"
        )
        self.assertEqual(
            visible.customer_invoice_count, 1, "counts only the active company"
        )

        one = as_user(
            context=dict(as_user.context, allowed_company_ids=[self.env.company.id])
        )
        self.assertEqual(
            partner.with_env(one).account_move_count,
            1,
            "account_move_count must key its cache on allowed_company_ids",
        )

    def test_invoice_edi_format_written_on_a_child_reaches_the_commercial_partner(self):
        selection = self.env["res.partner"]._fields["invoice_edi_format"].selection
        if not selection:
            self.skipTest("no e-invoicing format is installed")
        edi_format = selection[0][0]
        parent = self.env["res.partner"].create(
            {"name": "EdiParent", "is_company": True}
        )
        child = self.env["res.partner"].create(
            {"name": "EdiChild", "parent_id": parent.id}
        )

        child.invoice_edi_format = edi_format
        self.env.invalidate_all()

        self.assertEqual(
            child.invoice_edi_format,
            edi_format,
            "the value must survive a cache drop, not only the write",
        )
        self.assertEqual(parent.invoice_edi_format, edi_format)

    def test_clear_removed_edi_formats_clears_every_company(self):
        selection = self.env["res.partner"]._fields["invoice_edi_format"].selection
        if not selection:
            self.skipTest("no e-invoicing format is installed")
        edi_format = selection[0][0]
        other = self.setup_other_company()
        partner = self.env["res.partner"].create({"name": "EdiMultiCo"})
        partner.with_company(self.env.company).invoice_edi_format_store = edi_format
        partner.with_company(other["company"]).invoice_edi_format_store = edi_format

        malformed = self.env["res.partner"].create({"name": "EdiMalformed"})
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE res_partner SET invoice_edi_format_store = 'null'::jsonb WHERE id = %s",
            (malformed.id,),
        )

        self.env["res.partner"]._clear_removed_edi_formats(edi_format)

        self.assertFalse(
            partner.with_company(self.env.company).invoice_edi_format_store
        )
        self.assertFalse(
            partner.with_company(other["company"]).invoice_edi_format_store,
            "a second company kept a format its module no longer provides",
        )

    def test_parent_write_reports_the_vat_clash_without_a_singleton_error(self):
        parent = self.env["res.partner"].create({"name": "VatParent", "vat": "AAA"})
        with_moves = self.env["res.partner"].create(
            {"name": "VatWithMoves", "vat": "BBB"}
        )
        other = self.env["res.partner"].create({"name": "VatOther", "vat": "CCC"})
        self.init_invoice(
            "out_invoice",
            with_moves,
            invoice_date="2023-01-01",
            amounts=[100],
            post=True,
        )

        with self.assertRaisesRegex(UserError, "different"), self.cr.savepoint():
            (with_moves | other).write({"parent_id": parent.id})

    def test_parent_write_ignores_partners_without_accounting_entries(self):
        parent = self.env["res.partner"].create({"name": "OkParent", "vat": "AAA"})
        with_moves = self.env["res.partner"].create(
            {"name": "OkWithMoves", "vat": "AAA"}
        )
        no_moves = self.env["res.partner"].create(
            {"name": "OkNoMoves", "vat": "DIFFERENT"}
        )
        self.init_invoice(
            "out_invoice",
            with_moves,
            invoice_date="2023-01-01",
            amounts=[100],
            post=True,
        )

        (with_moves | no_moves).write({"parent_id": parent.id})

        self.assertEqual(with_moves.parent_id, parent)
        self.assertEqual(
            no_moves.parent_id,
            parent,
            "a partner with no accounting entry must not be blocked by a sibling",
        )

    def test_display_invoice_template_default_matches_the_journal(self):
        base = self.env.ref("account.account_invoices")
        base.copy({"name": "Invoice PDF variant"})
        self.env.registry.clear_cache()

        Partner = self.env["res.partner"]
        Journal = self.env["account.journal"]
        self.assertEqual(
            Partner.default_get(["display_invoice_template_pdf_report_id"])[
                "display_invoice_template_pdf_report_id"
            ],
            Journal.default_get(["display_invoice_template_pdf_report_id"])[
                "display_invoice_template_pdf_report_id"
            ],
            "a new partner hides the report selector the journal shows",
        )

    def test_available_invoice_templates_survive_a_multi_record_read(self):
        self.env.ref("account.account_invoices").copy({"name": "Template variant"})
        self.env.registry.clear_cache()
        self.env.invalidate_all()
        expected = len(
            self.env["account.move"]._get_available_invoice_template_pdf_report_ids()
        )
        self.assertGreater(expected, 1, "sanity: two templates exist")

        partners = self.env["res.partner"].create(
            [{"name": f"TemplateReader {i}"} for i in range(3)]
        )
        self.env.invalidate_all()
        self.assertEqual(
            [len(p.available_invoice_template_pdf_report_ids) for p in partners],
            [expected] * 3,
        )
        self.env["account.journal"].create(
            {"name": "Second Sales", "code": "SAL2", "type": "sale"}
        )
        journals = self.env["account.journal"].search([("type", "=", "sale")])
        self.assertGreater(len(journals), 1, "sanity: the fault needs two records")
        self.env.invalidate_all()
        self.assertEqual(
            [len(j.available_invoice_template_pdf_report_ids) for j in journals],
            [expected] * len(journals),
        )

    def test_company_registry_placeholder_reaches_the_company(self):
        japan = self.env["res.country"].search([("code", "=", "JP")], limit=1)
        self.assertTrue(japan, "sanity: JP is one of the seeded reference countries")
        expected = _ref_company_registry["jp"]

        partner = self.env["res.partner"].create(
            {"name": "RegistryPartner", "country_id": japan.id}
        )
        self.assertEqual(partner.company_registry_placeholder, expected)

        company = self.env["res.company"].create({"name": "RegistryCo"})
        company.partner_id.country_id = japan
        self.env.invalidate_all()
        self.assertEqual(
            company.company_registry_placeholder,
            expected,
            "the company reads the placeholder through base's related field",
        )

        belgium = self.env["res.country"].search([("code", "=", "BE")], limit=1)
        company.partner_id.country_id = belgium
        company.account_config_id.account_fiscal_country_id = japan
        self.env.invalidate_all()
        self.assertEqual(
            company.company_registry_placeholder,
            expected,
            "the fiscal country wins over the company's own country",
        )

    def test_vat_placeholder_comes_from_a_seam_not_a_reverse_import(self):
        Partner = self.env["res.partner"]
        japan = self.env["res.country"].search([("code", "=", "JP")], limit=1)
        self.assertEqual(Partner._get_expected_vat_format(False), "")

        partner = Partner.create({"name": "VatPartner", "country_id": japan.id})
        company = self.env["res.company"].create({"name": "VatCo"})
        company.partner_id.country_id = japan
        self.env.invalidate_all()
        expected = Partner._get_expected_vat_format("JP")

        if self.env["ir.module.module"].search_count(
            [("name", "=", "account_vat"), ("state", "=", "installed")]
        ):
            self.assertTrue(expected, "account_vat installed: the seam answers")
            self.assertIn(expected, partner.partner_vat_placeholder)
            self.assertIn(expected, company.account_config_id.company_vat_placeholder)
        else:
            self.assertEqual(expected, "")
            self.assertNotIn("7000012050002", partner.partner_vat_placeholder)
            self.assertNotIn(
                "7000012050002", company.account_config_id.company_vat_placeholder
            )

        for module in ("res_partner", "res_company"):
            source = file_open(
                f"account/models/{module}.py", "r", filter_ext=(".py",)
            ).read()
            self.assertNotIn(
                "account_vat",
                source,
                f"account/models/{module}.py imports from a module that depends on it",
            )

    def test_vendor_bills_button_agrees_with_what_it_opens(self):
        other = self.setup_other_company()
        parent = self.env["res.partner"].create({"name": "BillParent"})
        child = self.env["res.partner"].create(
            {"name": "BillChild", "parent_id": parent.id}
        )
        for partner, company in (
            (parent, self.env.company),
            (child, self.env.company),
            (parent, other["company"]),
        ):
            self.env["account.move"].with_company(company).create(
                {
                    "move_type": "in_invoice",
                    "invoice_date": "2023-01-01",
                    "partner_id": partner.id,
                    "invoice_line_ids": [
                        Command.create({"name": "l", "price_unit": 100})
                    ],
                }
            ).action_post()
        self.env.flush_all()
        self.env.invalidate_all()

        action = parent.action_view_partner_bills()
        opened = self.env["account.move"].search_count(action["domain"])
        self.assertEqual(
            parent.supplier_invoice_count,
            opened,
            "the badge and the list behind it must count the same moves",
        )
        self.assertEqual(parent.supplier_invoice_count, 2, "own bill + the child's")
        self.assertNotIn(
            "search_default_partner_id",
            action["context"],
            "the partner filter lives in the domain, which rolls children up",
        )

    def test_increase_rank_survives_a_concurrently_deleted_partner(self):
        partners = self.env["res.partner"].create(
            [{"name": f"RankRace {i}", "customer_rank": 3} for i in range(3)]
        )
        partners._increase_rank("customer_rank", 1)
        deleted_id = partners[1].id
        self.env.cr.execute("DELETE FROM res_partner WHERE id = %s", (deleted_id,))
        self.env.invalidate_all()

        with self.enter_registry_test_mode():
            self.env.cr.postcommit.run()

        self.env.invalidate_all()
        survivors = (partners[0] | partners[2]).exists()
        self.assertEqual(
            survivors.mapped("customer_rank"),
            [4, 4],
            "one deleted partner discarded the whole batch of increments",
        )
