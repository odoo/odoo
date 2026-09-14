from ast import literal_eval
from unittest.mock import patch

from odoo import Command, fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, HttpCase, new_test_user, tagged
from odoo.tools import hash_sign
from odoo.tools.misc import mute_logger

from odoo.addons.account.models.account_payment_method import AccountPaymentMethod
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.test_mail.data.test_mail_data import MAIL_EML_ATTACHMENT


@tagged("post_install", "-at_install")
class TestAccountJournal(AccountTestInvoicingCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency("EUR")
        cls.company_data_2 = cls.setup_other_company()

    def test_constraint_currency_consistency_with_accounts(self):
        journal_bank = self.company_data["default_journal_bank"]
        journal_bank.currency_id = self.other_currency

        with self.assertRaises(ValidationError):
            journal_bank.default_account_id.currency_id = self.company_data["currency"]

    def test_euro_payment_reference_generation(self):
        journal = self.company_data["default_journal_sale"]
        journal.invoice_reference_model = "euro"

        journal.code = "INV"
        invoice_valid = self.init_invoice("out_invoice", products=self.product_a)
        invoice_valid.journal_id = journal
        invoice_valid.action_post()
        self.assertTrue(
            invoice_valid.payment_reference, "A payment reference should be generated."
        )
        self.assertIn(
            "INV",
            invoice_valid.payment_reference.replace(" ", ""),
            "The reference should be based on the journal code.",
        )

        journal.code = "INV-"
        invoice_invalid = self.init_invoice("out_invoice", products=self.product_a)
        invoice_invalid.journal_id = journal
        invoice_invalid.action_post()
        self.assertTrue(
            invoice_invalid.payment_reference,
            "A payment reference should be generated.",
        )
        self.assertIn(
            str(journal.id),
            invoice_invalid.payment_reference.replace(" ", ""),
            "The reference should fall back to using the journal ID.",
        )

        journal.code = "INVα"
        invoice_unicode = self.init_invoice("out_invoice", products=self.product_a)
        invoice_unicode.journal_id = journal
        invoice_unicode.action_post()
        self.assertTrue(
            invoice_unicode.payment_reference,
            "A payment reference should be generated.",
        )
        self.assertIn(
            str(journal.id),
            invoice_unicode.payment_reference.replace(" ", ""),
            "The reference should fall back to using the journal ID for non-ASCII codes.",
        )

    def test_changing_journal_company(self):
        self.company_data["default_journal_sale"].code = "DIFFERENT"
        self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2019-01-01",
                "journal_id": self.company_data["default_journal_sale"].id,
            }
        )

        with self.assertRaisesRegex(UserError, "entries linked to it"):
            self.company_data["default_journal_sale"].company_id = self.company_data_2[
                "company"
            ]

    def test_account_journal_add_new_payment_method_multi(self):
        Method_get_payment_method_information = (
            AccountPaymentMethod._get_payment_method_information
        )

        def _get_payment_method_information(self):
            res = Method_get_payment_method_information(self)
            res["multi"] = {"mode": "multi", "type": ("bank",)}
            return res

        with patch.object(
            AccountPaymentMethod,
            "_get_payment_method_information",
            _get_payment_method_information,
        ):
            self.env["account.payment.method"].sudo().create(
                {"name": "Multi method", "code": "multi", "payment_type": "inbound"}
            )

        bank_journals_count = self.env["account.journal"].search_count(
            [("type", "=", "bank")]
        )
        edited_journals_count = self.env["account.journal"].search_count(
            [("inbound_payment_channel_ids.code", "=", "multi")]
        )

        self.assertEqual(bank_journals_count, edited_journals_count)

    def test_remove_payment_channels(self):
        first_method = self.inbound_payment_channel
        self.env["account.payment"].create(
            {
                "amount": 100.0,
                "payment_type": "inbound",
                "partner_type": "customer",
                "payment_channel_id": first_method.id,
            }
        )

        first_method.unlink()

        self.assertFalse(first_method.journal_id)

        second_method = self.outbound_payment_channel
        second_method.unlink()

        self.assertFalse(second_method.exists())

    def test_account_journal_duplicates(self):
        new_journals = (
            self.env["account.journal"]
            .with_context(import_file=True)
            .create(
                [
                    {"name": "OD_BLABLA"},
                    {"name": "OD_BLABLU"},
                ]
            )
        )

        self.assertEqual(
            sorted(new_journals.mapped("code")),
            ["MISC1", "OD_BL"],
            "The journals should be set correctly",
        )

    def test_archive_used_journal(self):
        journal = self.env["account.journal"].create(
            {
                "name": "Test Journal",
                "type": "sale",
                "code": "A",
            }
        )
        check_method = (
            self.env["account.payment.method"]
            .sudo()
            .create(
                {
                    "name": "Test",
                    "code": "check_printing_expense_test",
                    "payment_type": "outbound",
                }
            )
        )
        self.env["account.payment.channel"].create(
            {
                "name": "Check",
                "payment_method_id": check_method.id,
                "journal_id": journal.id,
            }
        )
        journal.action_archive()
        self.assertFalse(journal.active)

    def test_archive_multiple_journals(self):
        journals = self.env["account.journal"].create(
            [
                {"name": "Test Journal 1", "type": "sale", "code": "A1"},
                {"name": "Test Journal 2", "type": "sale", "code": "A2"},
            ]
        )

        journals.action_archive()
        self.assertFalse(journals[0].active)
        self.assertFalse(journals[1].active)

        journals.action_unarchive()
        self.assertTrue(journals[0].active)
        self.assertTrue(journals[1].active)

    def test_journal_notifications_unsubscribe(self):
        journal = self.company_data["default_journal_purchase"]
        journal.incoming_einvoice_notification_email = "test@example.com"

        self.authenticate(self.env.user.login, self.env.user.login)
        res = self.url_open(
            f"/my/journal/{journal.id}/unsubscribe",
            data={"csrf_token": http.Request.csrf_token(self)},
            method="POST",
        )
        res.raise_for_status()

        self.assertFalse(journal.incoming_einvoice_notification_email)

    def test_journal_notifications_unsubscribe_success(self):
        journal = self.company_data["default_journal_purchase"]
        email = "test@example.com"
        journal.incoming_einvoice_notification_email = email

        self.authenticate(None, None)
        token = hash_sign(
            self.env,
            journal._get_journal_notification_unsubscribe_scope(),
            {"email_to_unsubscribe": email, "journal_id": journal.id},
        )

        res = self.url_open(
            f"/my/journal/{journal.id}/unsubscribe?token={token}",
            data={"csrf_token": http.Request.csrf_token(self)},
            method="POST",
        )
        res.raise_for_status()

        self.assertFalse(journal.incoming_einvoice_notification_email)

    def test_journal_notifications_unsubscribe_without_token_nor_access(self):
        journal = self.company_data["default_journal_purchase"]
        email = "test@example.com"
        journal.incoming_einvoice_notification_email = email

        self.authenticate(None, None)
        with mute_logger("odoo.http"):
            res = self.url_open(
                f"/my/journal/{journal.id}/unsubscribe",
                data={"csrf_token": http.Request.csrf_token(self)},
                method="POST",
            )
        self.assertEqual(res.status_code, 403)
        self.assertIn(
            "Invoice Notifications",
            res.text,
            "the route should answer with its own page, not an AccessError",
        )
        self.assertEqual(journal.incoming_einvoice_notification_email, email)

    def test_journal_notifications_unsubscribe_errors(self):
        journal = self.company_data["default_journal_purchase"]
        email = "test@example.com"
        self.authenticate(None, None)
        valid_token = hash_sign(
            self.env(su=True),
            journal._get_journal_notification_unsubscribe_scope(),
            {"email_to_unsubscribe": email, "journal_id": journal.id},
        )

        def _get_token():
            return

        def _unsubscribe(token, journal_id=journal.id):
            return self.url_open(
                f"/my/journal/{journal_id}/unsubscribe?token={token}",
                data={"csrf_token": http.Request.csrf_token(self)},
                method="POST",
            )

        with self.subTest("invalid_token"):
            journal.incoming_einvoice_notification_email = email
            res = _unsubscribe("invalid_token")
            self.assertEqual(res.status_code, 403)
            self.assertEqual(journal.incoming_einvoice_notification_email, email)

        with self.subTest("already_unsubscribed"):
            journal.incoming_einvoice_notification_email = email
            first_unsubscribe = _unsubscribe(valid_token)
            first_unsubscribe.raise_for_status()
            self.assertFalse(journal.incoming_einvoice_notification_email)
            second_unsubscribe = _unsubscribe(valid_token)
            self.assertEqual(second_unsubscribe.status_code, 404)

        with self.subTest("wrong_journal_id"):
            journal.incoming_einvoice_notification_email = email
            res = _unsubscribe(valid_token, journal_id=journal.id + 1)
            self.assertEqual(res.status_code, 403)
            self.assertEqual(journal.incoming_einvoice_notification_email, email)

    def test_write_type_resets_default_account_id(self):
        company = self.env.company
        journal = self.env["account.journal"].create(
            {
                "name": "test_write_type_resets",
                "code": "TWTR",
                "type": "sale",
                "company_id": company.id,
                "default_account_id": company.income_account_id.id,
            }
        )
        self.assertEqual(journal.default_account_id, company.income_account_id)

        journal.write({"type": "purchase"})
        self.assertEqual(
            journal.default_account_id,
            company.expense_account_id,
            "the stale sale-type account must be reset when type changes via write()",
        )

    def test_batch_type_change_on_same_named_journals_does_not_crash(self):
        company = self.env.company
        journals = self.env["account.journal"].create(
            [
                {
                    "name": "Vendor",
                    "code": "ZZ01",
                    "type": "general",
                    "company_id": company.id,
                },
                {
                    "name": "Vendor",
                    "code": "ZZ02",
                    "type": "general",
                    "company_id": company.id,
                },
            ]
        )
        journals.write({"type": "purchase"})
        self.assertEqual(journals.mapped("type"), ["purchase", "purchase"])
        self.assertNotEqual(
            journals[0].alias_name,
            journals[1].alias_name,
            "two same-named journals must not end up sharing one alias",
        )

    def test_ledger_groups_come_back_in_the_order_they_were_dragged_into(self):
        """`account_journal_views.xml` puts `widget="handle"` on the ledger-group
        list, and `_get_filter_journal_groups` already asks for `order="sequence"`
        by hand -- the model simply never declared it, so every other reader,
        the settings list included, got id order.
        """
        Group = self.env["account.journal.group"]
        groups = Group.create(
            [
                {"name": "Third", "sequence": 30},
                {"name": "Second", "sequence": 20},
                {"name": "First", "sequence": 10},
            ]
        )
        self.env.flush_all()
        self.env.invalidate_all()

        found = Group.search([("id", "in", groups.ids)])

        self.assertEqual(found.mapped("name"), ["First", "Second", "Third"])

    def test_ledger_groups_at_the_default_sequence_keep_a_stable_order(self):
        """Every row in an existing database sits at the default sequence, so the
        case that matters is the tie: a sort key with no tiebreak would order
        them however the query plan came out."""
        Group = self.env["account.journal.group"]
        tied = Group.create([{"name": f"Tied {index}"} for index in range(6)])
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(len(set(tied.mapped("sequence"))), 1, "the fixture must tie")

        orders = [Group.search([("id", "in", tied.ids)]).ids for _ in range(4)]

        self.assertEqual(orders[0], sorted(tied.ids))
        self.assertTrue(all(order == orders[0] for order in orders))


@tagged("post_install", "-at_install")
class TestAccountJournalSelectableDomain(AccountTestInvoicingCommon):
    def _domain_for(self, move_type="out_invoice"):
        move = self.env["account.move"].new(
            {"move_type": move_type, "company_id": self.env.company.id}
        )
        return move.journal_id_domain

    def test_domain_is_computed_not_a_static_string(self):
        field = self.env["account.move"]._fields["journal_id"]
        self.assertEqual(
            field.domain,
            "journal_id_domain",
            "journal_id must read its domain from the computed field, so that an "
            "extension can narrow the selection without patching the view",
        )

    def test_domain_offers_every_suitable_journal_by_default(self):
        domain = self._domain_for()
        selectable = self.env["account.journal"].search(domain)
        suitable = self.env["account.move"]._get_suitable_journal_ids("out_invoice")
        self.assertEqual(
            selectable,
            suitable,
            "with no extension in play the domain must not narrow anything",
        )

    def test_domain_still_honours_move_type_suitability(self):
        purchase_journal = self.env["account.journal"].create(
            {"name": "Selectable purchases", "code": "SELP", "type": "purchase"}
        )
        selectable = self.env["account.journal"].search(self._domain_for())
        self.assertNotIn(
            purchase_journal,
            selectable,
            "a purchase journal is never selectable on a customer invoice",
        )

    def _with_narrowed_selection(self, excluded):
        AccountJournal = type(self.env["account.journal"])
        original = AccountJournal._get_domain_selectable

        def narrowed(journal_self):
            return [*original(journal_self), ("id", "!=", excluded.id)]

        AccountJournal._get_domain_selectable = narrowed
        self.env["account.move"].invalidate_model(["journal_id_domain"])
        self.addCleanup(setattr, AccountJournal, "_get_domain_selectable", original)

    def test_a_narrowed_journal_is_refused_on_write(self):
        journals = self.env["account.journal"].search(
            [
                ("type", "=", "sale"),
                *self.env["account.journal"]._check_company_domain(self.env.company),
            ]
        )
        if len(journals) < 2:
            journals |= self.env["account.journal"].create(
                {"name": "Selectable second sale", "code": "SEL2", "type": "sale"}
            )
        allowed, excluded = journals[0], journals[1]
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-03-01",
                "journal_id": allowed.id,
            }
        )
        self._with_narrowed_selection(excluded)
        with self.assertRaises(
            ValidationError,
            msg=(
                "a domain is only a UI filter -- the narrowing has to be enforced by a "
                "constraint or a plain write walks straight past it"
            ),
        ):
            move.write({"journal_id": excluded.id})

    def test_a_narrowed_journal_is_refused_on_create(self):
        journals = self.env["account.journal"].search(
            [
                ("type", "=", "sale"),
                *self.env["account.journal"]._check_company_domain(self.env.company),
            ]
        )
        if len(journals) < 2:
            journals |= self.env["account.journal"].create(
                {"name": "Selectable third sale", "code": "SEL3", "type": "sale"}
            )
        excluded = journals[1]
        self._with_narrowed_selection(excluded)
        with self.assertRaises(ValidationError):
            self.env["account.move"].create(
                {
                    "move_type": "out_invoice",
                    "partner_id": self.partner_a.id,
                    "invoice_date": "2026-03-01",
                    "journal_id": excluded.id,
                }
            )

    def test_core_narrows_only_by_the_allowed_user_list(self):
        self.assertEqual(
            self.env["account.journal"]._get_domain_selectable(),
            [
                "|",
                ("allowed_user_ids", "=", False),
                ("allowed_user_ids", "in", [self.env.uid]),
            ],
            "the only clause core contributes is allowed_user_ids, which is "
            "vacuous until a journal names its users",
        )

    def test_an_extension_can_narrow_the_selection(self):
        excluded = self.env["account.journal"].create(
            {"name": "Selectable excluded", "code": "SELX", "type": "sale"}
        )
        AccountJournal = type(self.env["account.journal"])
        original = AccountJournal._get_domain_selectable

        def narrowed(journal_self):
            return [*original(journal_self), ("id", "!=", excluded.id)]

        AccountJournal._get_domain_selectable = narrowed
        try:
            self.env["account.move"].invalidate_model(["journal_id_domain"])
            selectable = self.env["account.journal"].search(self._domain_for())
        finally:
            AccountJournal._get_domain_selectable = original
        self.assertNotIn(
            excluded,
            selectable,
            "a clause returned by _get_domain_selectable must reach journal_id_domain",
        )
        self.assertTrue(
            selectable,
            "narrowing must remove one journal, not empty the selection",
        )


@tagged("post_install", "-at_install")
class TestAccountJournalAllowedAccounts(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls.company_data["default_journal_sale"]
        cls.income = cls.company_data["default_account_revenue"]
        cls.receivable = cls.company_data["default_account_receivable"]
        cls.outsider = cls.company_data["default_account_expense"]

    def _invoice(self, account):
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-03-01",
                "journal_id": self.journal.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "line",
                            "quantity": 1,
                            "price_unit": 100.0,
                            "account_id": account.id,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )

    def test_an_empty_list_allows_every_account(self):
        self.assertFalse(self.journal.allowed_account_ids)

        self._invoice(self.outsider).action_post()

    def test_a_listed_account_posts(self):
        self.journal.allowed_account_ids = self.income | self.receivable

        invoice = self._invoice(self.income)
        invoice.action_post()

        self.assertEqual(invoice.state, "posted")

    def test_an_unlisted_account_is_refused_on_post(self):
        self.journal.allowed_account_ids = self.income | self.receivable
        invoice = self._invoice(self.outsider)

        with self.assertRaises(UserError):
            invoice.action_post()

    def test_an_unlisted_account_is_refused_on_write(self):
        self.journal.allowed_account_ids = self.income | self.receivable
        invoice = self._invoice(self.income)

        with self.assertRaises(UserError):
            invoice.invoice_line_ids.write({"account_id": self.outsider.id})

    def test_the_journal_own_accounts_never_need_listing(self):
        self.journal.default_account_id = self.income
        self.journal.allowed_account_ids = self.receivable

        self.assertTrue(self.journal._is_account_allowed(self.income))
        self.assertFalse(self.journal._is_account_allowed(self.outsider))

    def test_a_suspense_account_is_structural_too(self):
        bank = self.company_data["default_journal_bank"]
        bank.allowed_account_ids = self.receivable

        self.assertTrue(bank._is_account_allowed(bank.suspense_account_id))

    def test_narrowing_the_list_below_existing_items_is_refused(self):
        self._invoice(self.outsider).action_post()

        with self.assertRaises(ValidationError):
            self.journal.allowed_account_ids = self.income | self.receivable

    def test_narrowing_the_list_above_existing_items_is_accepted(self):
        invoice = self._invoice(self.income)
        invoice.action_post()

        self.journal.allowed_account_ids = (
            self.income | self.receivable | invoice.line_ids.account_id
        )

        self.assertTrue(self.journal.allowed_account_ids)

    def test_a_cancelled_entry_does_not_pin_the_list(self):
        invoice = self._invoice(self.outsider)
        invoice.action_post()
        invoice.action_cancel()
        self.assertEqual(invoice.state, "cancel")

        self.journal.allowed_account_ids = self.income | self.receivable

        self.assertEqual(
            self.journal.allowed_account_ids, self.income | self.receivable
        )


@tagged("post_install", "-at_install")
class TestAccountJournalUserAccess(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.restricted_journal = cls.env["account.journal"].create(
            {"name": "Restricted", "code": "RSTR", "type": "sale"}
        )
        cls.open_journal = cls.env["account.journal"].create(
            {"name": "Open", "code": "OPEN", "type": "sale"}
        )
        cls.allowed_user = cls._create_accountant("journal_allowed")
        cls.other_user = cls._create_accountant("journal_other")
        cls.restricted_journal.allowed_user_ids = cls.allowed_user

    @classmethod
    def _create_accountant(cls, login):
        return cls.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "company_id": cls.env.company.id,
                "company_ids": [(6, 0, cls.env.company.ids)],
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("account.group_account_user").id,
                        ],
                    )
                ],
            }
        )

    def _journal_domain(self, user):
        move = (
            self.env["account.move"]
            .with_user(user)
            .new({"move_type": "out_invoice", "company_id": self.env.company.id})
        )
        return move.journal_id_domain

    def _selectable(self, user):
        return (
            self.env["account.journal"]
            .with_user(user)
            .search(self._journal_domain(user))
        )

    def test_a_journal_without_a_list_is_open_to_everyone(self):
        self.assertIn(self.open_journal, self._selectable(self.other_user))

    def test_a_restricted_journal_is_hidden_from_other_users(self):
        self.assertNotIn(self.restricted_journal, self._selectable(self.other_user))

    def test_a_restricted_journal_is_offered_to_a_listed_user(self):
        self.assertIn(self.restricted_journal, self._selectable(self.allowed_user))

    def test_the_domain_still_honours_move_type_suitability(self):
        purchase_journal = self.env["account.journal"].create(
            {"name": "Purchases", "code": "PURJ", "type": "purchase"}
        )

        self.assertNotIn(purchase_journal, self._selectable(self.allowed_user))

    def _create_invoice(self, user, journal):
        return (
            self.env["account.move"]
            .with_user(user)
            .create(
                {
                    "move_type": "out_invoice",
                    "partner_id": self.partner_a.id,
                    "invoice_date": "2026-03-01",
                    "journal_id": journal.id,
                }
            )
        )

    def test_an_unlisted_user_is_refused_the_journal_not_merely_shown_less(self):
        with self.assertRaises(ValidationError):
            self._create_invoice(self.other_user, self.restricted_journal)

    def test_a_listed_user_may_actually_post_to_the_journal(self):
        invoice = self._create_invoice(self.allowed_user, self.restricted_journal)

        self.assertEqual(invoice.journal_id, self.restricted_journal)

    def test_a_journal_without_a_list_is_writable_by_anyone(self):
        invoice = self._create_invoice(self.other_user, self.open_journal)

        self.assertEqual(invoice.journal_id, self.open_journal)


@tagged("post_install", "-at_install", "mail_alias")
class TestAccountJournalAlias(AccountTestInvoicingCommon, MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()

    def test_alias_name_creation(self):
        journal1 = self.company_data["default_journal_purchase"]
        company1 = journal1.company_id
        journal2 = self.company_data_2["default_journal_sale"]
        company2 = journal2.company_id
        company2.name = "ぁ"

        for (aname, jname, jcode, jtype, jcompany), expected_alias_name in zip(
            [
                ("youpie", "Journal Name", "NEW1", "purchase", company1),
                (False, "Journal Other Name", "NEW2", "purchase", company1),
                (False, "ぁ", "NEW3", "purchase", company1),
                (False, "ぁ", "ぁ", "purchase", company1),
                ("youpie", "Journal Name", "NEW1", "purchase", company2),
                (False, "Journal Other Name", "NEW2", "purchase", company2),
                (False, "ぁ", "NEW3", "purchase", company2),
                (False, "ぁ", "ぁ", "purchase", company2),
            ],
            [
                f"youpie-{company1.name}",
                f"journal-other-name-{company1.name}",
                f"new3-{company1.name}",
                f"purchase-{company1.name}",
                f"youpie-{company2.id}",
                f"journal-other-name-{company2.id}",
                f"new3-{company2.id}",
                f"purchase-{company2.id}",
            ],
            strict=False,
        ):
            with self.subTest(
                aname=aname, jname=jname, jcode=jcode, jtype=jtype, jcompany=jcompany
            ):
                new_journal = self.env["account.journal"].create(
                    {
                        "code": jcode,
                        "company_id": jcompany.id,
                        "name": jname,
                        "type": jtype,
                        **({"alias_name": aname} if aname else {}),
                    }
                )
                self.assertEqual(new_journal.alias_name, expected_alias_name)

        journals = self.env["account.journal"].create(
            [
                {"code": f"NEW{jtype}", "name": f"Type {jtype}", "type": jtype}
                for jtype in ("general", "cash", "bank")
            ]
        )
        self.assertFalse(journals.alias_id, "Do not create useless aliases")
        self.assertFalse(list(filter(None, journals.mapped("alias_name"))))

    def test_alias_name_form(self):
        journal = Form(self.env["account.journal"])
        journal.name = "Test With Form"
        self.assertFalse(journal.alias_name)
        journal.type = "sale"
        self.assertEqual(journal.alias_name, f"test-with-form-{self.env.company.name}")
        journal.type = "cash"
        self.assertFalse(journal.alias_name)

    def test_alias_from_type(self):
        journal = self.company_data["default_journal_purchase"]

        company_name = "company_1_data"
        journal_code = "BILL"
        journal_name = "Purchases"
        journal_alias = journal.alias_id
        self.assertEqual(journal.code, journal_code)
        self.assertEqual(journal.company_id.name, company_name)
        self.assertEqual(journal.name, journal_name)
        self.assertEqual(journal.type, "purchase")

        self.assertEqual(journal_alias.alias_contact, "everyone")
        self.assertDictEqual(
            dict(literal_eval(journal_alias.alias_defaults)),
            {
                "move_type": "in_invoice",
                "company_id": journal.company_id.id,
                "journal_id": journal.id,
            },
        )
        self.assertFalse(
            journal_alias.alias_force_thread_id, "Journal alias should create new moves"
        )
        self.assertEqual(
            journal_alias.alias_model_id,
            self.env["ir.model"]._get("account.move"),
            "Journal alias targets moves",
        )
        self.assertEqual(journal_alias.alias_name, f"purchases-{company_name}")
        self.assertEqual(
            journal_alias.alias_parent_model_id,
            self.env["ir.model"]._get("account.journal"),
            "Journal alias owned by journal itself",
        )
        self.assertEqual(
            journal_alias.alias_parent_thread_id,
            journal.id,
            "Journal alias owned by journal itself",
        )

        for alias_name, expected in [
            (False, False),
            ("", False),
            (" ", f"purchases-{company_name}"),
            (".", f"purchases-{company_name}"),
            ("😊", f"purchases-{company_name}"),
            ("ぁ", f"purchases-{company_name}"),
            ("Youpie Boum", "youpie-boum"),
        ]:
            with self.subTest(alias_name=alias_name):
                journal.write({"alias_name": alias_name})
                self.assertEqual(journal.alias_name, expected)
                self.assertEqual(journal_alias.alias_name, expected)

        for jtype in ("general", "cash", "bank"):
            journal.write({"type": jtype})
            self.assertEqual(
                journal.alias_id,
                journal_alias,
                "Dà not unlink aliases, just reset their value",
            )
            self.assertFalse(journal.alias_name)
            self.assertFalse(journal_alias.alias_name)

        journal.company_id.write({"name": "New Company Name"})
        journal.write({"name": "Reset Journal", "type": "sale"})
        journal_alias_2 = journal.alias_id
        self.assertEqual(journal_alias_2.alias_contact, "everyone")
        self.assertDictEqual(
            dict(literal_eval(journal_alias_2.alias_defaults)),
            {
                "move_type": "out_invoice",
                "company_id": journal.company_id.id,
                "journal_id": journal.id,
            },
        )
        self.assertFalse(
            journal_alias_2.alias_force_thread_id,
            "Journal alias should create new moves",
        )
        self.assertEqual(
            journal_alias_2.alias_model_id,
            self.env["ir.model"]._get("account.move"),
            "Journal alias targets moves",
        )
        self.assertEqual(journal_alias_2.alias_name, "reset-journal-new-company-name")
        self.assertEqual(
            journal_alias_2.alias_parent_model_id,
            self.env["ir.model"]._get("account.journal"),
            "Journal alias owned by journal itself",
        )
        self.assertEqual(
            journal_alias_2.alias_parent_thread_id,
            journal.id,
            "Journal alias owned by journal itself",
        )

    def test_a_falsy_alias_name_asks_for_no_alias(self):
        self.env["mail.alias"].create(
            {"alias_model_id": self.env["ir.model"]._get_id("account.move")}
        )
        for index, asked in enumerate((False, "")):
            with self.subTest(alias_name=asked):
                journal = self.env["account.journal"].create(
                    {
                        "name": f"No alias {index}",
                        "type": "sale",
                        "code": f"NAL{index}",
                        "alias_name": asked,
                    }
                )
                self.assertFalse(journal.alias_name)
                self.assertFalse(journal.alias_id)

    def test_a_colliding_alias_is_suffixed_with_the_real_code(self):
        first, second = self.env["account.journal"].create(
            [
                {"name": "Same Name", "type": "sale"},
                {"name": "Same Name", "type": "sale"},
            ]
        )
        self.env.flush_all()
        self.assertNotEqual(first.alias_name, second.alias_name)
        self.assertTrue(
            second.alias_name.endswith(second.code.lower()),
            f"{second.alias_name!r} must be disambiguated by {second.code!r}",
        )

    def test_alias_create_unique(self):
        company_name = self.company_data["company"].name
        journal = self.env["account.journal"].create(
            {
                "name": "Test Journal",
                "type": "sale",
                "code": "A",
            }
        )
        journal2 = self.env["account.journal"].create(
            {
                "name": "Test Journal",
                "type": "sale",
                "code": "B",
            }
        )
        self.assertEqual(journal.alias_name, f"test-journal-{company_name}")
        self.assertEqual(journal2.alias_name, f"test-journal-{company_name}-b")

    def test_non_latin_journal_code_payment_reference(self):
        non_latin_code = "TΠY"
        latin_code = "TPY"

        journal_non_latin = self.env["account.journal"].create(
            {
                "name": "Test Journal",
                "type": "sale",
                "code": non_latin_code,
                "invoice_reference_model": "euro",
            }
        )
        journal_latin = self.env["account.journal"].create(
            {
                "name": "Test Journal",
                "type": "sale",
                "code": latin_code,
                "invoice_reference_model": "euro",
            }
        )

        invoice_non_latin = self.init_invoice(
            move_type="out_invoice",
            partner=self.partner_a,
            invoice_date=fields.Date.today(),
            post=True,
            products=[self.product_a],
            journal=journal_non_latin,
        )
        invoice_latin = self.init_invoice(
            move_type="out_invoice",
            partner=self.partner_a,
            invoice_date=fields.Date.today(),
            post=True,
            products=[self.product_a],
            journal=journal_latin,
        )

        def reference_body(invoice):
            return invoice.payment_reference.replace(" ", "")[4:]

        expected_id = str(invoice_non_latin.journal_id.id)
        self.assertEqual(
            reference_body(invoice_non_latin)[: len(expected_id)],
            expected_id,
            "The reference should start with " + expected_id,
        )

        self.assertIn(
            reference_body(invoice_latin)[:3],
            latin_code,
            f"Expected journal code '{latin_code}' at the start of the reference body",
        )

    def test_use_default_account_from_journal(self):
        autobalance_account = self.env["account.account"].create(
            {
                "name": "Autobalance Account",
                "account_type": "income",
                "code": "A",
            }
        )
        journal = self.env["account.journal"].create(
            {
                "name": "Test Journal",
                "type": "general",
                "code": "B",
                "default_account_id": autobalance_account.id,
            }
        )

        entry = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": journal.id,
                "line_ids": [
                    Command.create(
                        {
                            "debit": 100.0,
                            "credit": 0.0,
                            "tax_ids": (self.company_data["default_tax_sale"]),
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                        }
                    )
                ],
            }
        )

        entry.action_post()
        self.assertRecordValues(
            entry.line_ids,
            [
                {
                    "balance": 100.0,
                    "account_id": self.company_data["default_account_revenue"].id,
                },
                {
                    "balance": 15.0,
                    "account_id": self.company_data["default_account_tax_sale"].id,
                },
                {"balance": -115.0, "account_id": autobalance_account.id},
            ],
        )

    def test_send_email_to_alias_from_other_company(self):
        user_company_2 = new_test_user(
            self.env,
            name="company 2 user",
            login="company_2_user",
            password="company_2_user",
            email="company_2_user@test.com",
            company_id=self.company_data_2["company"].id,
        )
        self.format_and_process(
            MAIL_EML_ATTACHMENT,
            user_company_2.email,
            self.company_data["default_journal_purchase"].alias_email,
            subject="purchase test mail",
            target_model="account.move",
            msg_id="<test-account-move-alias-id>",
        )
        self.assertTrue(
            self.env["account.move"].search(
                [("invoice_source_email", "=", "company_2_user@test.com")]
            )
        )

    def test_alias_uniqueness_without_domain(self):
        default_account = self.env["account.account"].search(
            domain=[("account_type", "in", ("income", "income_other"))],
            limit=1,
        )
        with Form(self.env["account.journal"]) as journal_form:
            journal_form.type = "sale"
            journal_form.code = "A"
            journal_form.name = "Test Journal 1"
            journal_form.default_account_id = default_account
            journal_1 = journal_form.save()
        with Form(self.env["account.journal"]) as journal_form:
            journal_form.type = "sale"
            journal_form.code = "B"
            journal_form.name = "Test Journal 2"
            journal_form.default_account_id = default_account
            journal_2 = journal_form.save()
        self.assertNotEqual(
            journal_1.alias_id.alias_name, journal_2.alias_id.alias_name
        )

    def test_payment_channel_accounts_on_recompute(self):
        bank_journal = self.company_data["default_journal_bank"]
        outstanding_receipt_account = self.env["account.chart.template"].ref(
            "account_journal_payment_debit_account_id"
        )
        outstanding_payment_account = self.env["account.chart.template"].ref(
            "account_journal_payment_credit_account_id"
        )

        inbound_method_lines = bank_journal.inbound_payment_channel_ids
        inbound_method_lines_names = inbound_method_lines.mapped("name")
        inbound_method_lines[0].payment_account_id = outstanding_receipt_account

        outbound_method_lines = bank_journal.outbound_payment_channel_ids
        outbound_method_lines_names = outbound_method_lines.mapped("name")
        outbound_method_lines[0].payment_account_id = outstanding_payment_account
        new_outbound_payment_line = outbound_method_lines[0].copy(
            {
                "payment_account_id": self.company_data[
                    "default_account_deferred_expense"
                ].id
            }
        )
        bank_journal.outbound_payment_channel_ids = [
            Command.link(new_outbound_payment_line.id)
        ]

        bank_journal.currency_id = self.company_data["currency"]

        self.assertRecordValues(
            bank_journal.inbound_payment_channel_ids,
            [
                {
                    "name": name,
                    "payment_account_id": outstanding_receipt_account.id
                    if index == 0
                    else False,
                }
                for index, name in enumerate(inbound_method_lines_names)
            ],
        )
        self.assertRecordValues(
            bank_journal.outbound_payment_channel_ids,
            [
                {
                    "name": name,
                    "payment_account_id": outstanding_payment_account.id
                    if index == 0
                    else False,
                }
                for index, name in enumerate(outbound_method_lines_names)
            ],
        )


@tagged("post_install", "-at_install")
class TestAccountJournalTypeDefaults(AccountTestInvoicingCommon):
    def _create(self, journal_type, code, **vals):
        return self.env["account.journal"].create(
            {"name": f"T {code}", "type": journal_type, "code": code, **vals}
        )

    def _convert(self, journal_type, code):
        journal = self._create("general", code)
        self.env.flush_all()
        journal.write({"type": journal_type})
        return journal

    def test_create_and_write_agree_on_the_default_account(self):
        for journal_type, code_a, code_b in (
            ("sale", "TDA1", "TDA2"),
            ("purchase", "TDB1", "TDB2"),
        ):
            with self.subTest(journal_type=journal_type):
                self.assertEqual(
                    self._create(journal_type, code_a).default_account_id,
                    self._convert(journal_type, code_b).default_account_id,
                    "create() and write({'type': ...}) must pick the same account",
                )

    def test_the_default_account_comes_from_the_company(self):
        other_income = self.env["account.account"].create(
            {
                "name": "Other income",
                "code": "409999",
                "account_type": "income_other",
                "company_ids": [Command.link(self.env.company.id)],
            }
        )
        self.env["ir.default"].set(
            "product.category",
            "property_account_income_categ_id",
            other_income.id,
            company_id=self.env.company.id,
        )
        self.env.registry.clear_cache()
        self.assertEqual(
            self._create("sale", "TDC1").default_account_id,
            self.env.company.income_account_id,
            "a product-category default must not outrank the company's income account",
        )

    def test_an_archived_account_is_never_defaulted_onto_a_journal(self):
        self.env.company.income_account_id.active = False
        self.env.flush_all()
        self.env.registry.clear_cache()
        self.assertFalse(self._create("sale", "TDD1").default_account_id)
        self.assertFalse(self._convert("sale", "TDD2").default_account_id)

    def test_converting_to_a_liquidity_type_provides_an_account(self):
        for journal_type, code in (
            ("bank", "TDE1"),
            ("cash", "TDE2"),
            ("credit", "TDE3"),
        ):
            with self.subTest(journal_type=journal_type):
                self.assertTrue(
                    self._convert(journal_type, code).default_account_id,
                    "a liquidity journal without a default account cannot post",
                )

    def test_a_journal_created_without_a_name_gets_one(self):
        for journal_type, code in (
            ("bank", "TDF1"),
            ("cash", "TDF2"),
            ("credit", "TDF3"),
            ("sale", "TDF4"),
            ("general", "TDF5"),
        ):
            with self.subTest(journal_type=journal_type):
                journal = self.env["account.journal"].create(
                    {"type": journal_type, "code": code}
                )
                self.assertTrue(journal.name)
                if journal_type in ("bank", "cash", "credit"):
                    self.assertTrue(
                        journal.default_account_id.name,
                        "the account created alongside the journal needs a name too",
                    )

    def test_an_explicit_account_survives_a_type_change(self):
        journal = self._create("sale", "TDG1")
        expense = self.env.company.expense_account_id
        journal.write({"type": "purchase", "default_account_id": expense.id})
        self.assertEqual(journal.default_account_id, expense)

    def test_a_stale_cash_difference_account_is_cleared(self):
        journal = self._create("bank", "TDH1")
        self.assertTrue(journal.profit_account_id)
        journal.write(
            {"type": "general", "profit_account_id": journal.profit_account_id.id}
        )
        self.assertFalse(
            journal.loss_account_id,
            "a cash-difference account must not survive onto a non-cash journal",
        )


@tagged("post_install", "-at_install")
class TestAccountJournalCodeAndCopy(AccountTestInvoicingCommon):
    def test_copy_honours_an_explicit_default(self):
        journal = self.env["account.journal"].create(
            {"name": "Original", "type": "sale", "code": "TCA1"}
        )
        copied = journal.copy(default={"code": "TCA9", "name": "Chosen name"})
        self.assertEqual(copied.code, "TCA9")
        self.assertEqual(copied.name, "Chosen name")

    def test_copy_without_a_default_still_disambiguates(self):
        journal = self.env["account.journal"].create(
            {"name": "Original", "type": "sale", "code": "TCB1"}
        )
        copied = journal.copy()
        self.assertNotEqual(copied.code, journal.code)
        self.assertNotEqual(copied.name, journal.name)

    def test_a_user_chosen_code_survives_a_type_change(self):
        journal = self.env["account.journal"].create(
            {"name": "Chosen", "type": "sale", "code": "ZS1"}
        )
        values = journal.onchange(
            {"id": journal.id, "name": "Chosen", "type": "purchase", "code": "ZS1"},
            ["type"],
            {"type": {}, "code": {}, "name": {}},
        ).get("value", {})
        self.assertEqual(values.get("code", "ZS1"), "ZS1")

    def test_a_generated_code_is_refreshed_on_a_type_change(self):
        journal = self.env["account.journal"].create(
            {"name": "Generated", "type": "sale", "code": "INV9"}
        )
        values = journal.onchange(
            {"id": journal.id, "name": "Generated", "type": "purchase", "code": "INV9"},
            ["type"],
            {"type": {}, "code": {}, "name": {}},
        ).get("value", {})
        self.assertTrue(values.get("code", "").startswith("BILL"))

    def test_writing_an_unusable_alias_on_several_journals_that_share_a_name(self):
        journals = self.env["account.journal"].create(
            [
                {"name": "Twins", "type": "sale", "code": "TWN1"},
                {"name": "Twins", "type": "sale", "code": "TWN2"},
            ]
        )
        journals.write({"alias_name": "δοκιμή"})
        self.env.flush_all()
        self.assertEqual(len(set(journals.mapped("alias_name"))), 2)

    def test_writing_an_unusable_alias_on_several_journals(self):
        journals = self.env["account.journal"].create(
            [
                {"name": "A", "type": "sale", "code": "TCC1"},
                {"name": "B", "type": "sale", "code": "TCC2"},
            ]
        )
        journals.write({"alias_name": "δοκιμή"})
        self.assertEqual(len(set(journals.mapped("alias_name"))), 2)

    def test_an_unknown_payment_type_is_refused(self):
        journal = self.env["account.journal"].create(
            {"name": "Bank", "type": "bank", "code": "TCD1"}
        )
        with self.assertRaises(ValueError):
            journal._get_available_payment_channels("bogus")

    def test_an_unset_payment_type_has_no_channels(self):
        journal = self.env["account.journal"].create(
            {"name": "Bank", "type": "bank", "code": "TCD2"}
        )
        self.assertTrue(journal.outbound_payment_channel_ids)
        self.assertFalse(journal._get_available_payment_channels(False))

    def test_no_default_account_outside_the_liquidity_types(self):
        with self.assertRaises(UserError):
            self.env["account.journal"]._create_default_account(
                self.env.company, "general", {"name": "x"}
            )

    def test_a_code_spelled_out_later_in_the_batch_is_still_reserved(self):
        journals = self.env["account.journal"].create(
            [
                {"name": "Auto", "type": "bank"},
                {"name": "Chosen", "type": "bank", "code": "BNK2"},
                {"name": "Auto too", "type": "bank"},
            ]
        )
        self.env.flush_all()
        codes = journals.mapped("code")
        self.assertEqual(len(set(codes)), 3, f"codes must be distinct, got {codes}")
        self.assertIn("BNK2", codes)

    def test_unnamed_journals_of_one_type_are_named_apart(self):
        journals = self.env["account.journal"].create(
            [{"type": "bank"} for _ in range(3)]
        )
        self.env.flush_all()
        names = journals.mapped("name")
        self.assertEqual(len(set(names)), 3, f"names must be distinct, got {names}")

    def test_several_unnamed_sale_journals_can_be_created_at_once(self):
        journals = self.env["account.journal"].create(
            [{"type": "sale"} for _ in range(3)]
        )
        self.env.flush_all()
        self.assertEqual(len(set(journals.mapped("alias_name"))), 3)


@tagged("post_install", "-at_install")
class TestAccountJournalTypeMetadata(AccountTestInvoicingCommon):
    def test_the_type_families_are_derived_from_one_dict(self):
        from odoo.addons.account.models.account_journal import (
            CASH_DIFFERENCE_TYPES,
            DOCUMENT_TYPES,
            JOURNAL_TYPES,
            LIQUIDITY_TYPES,
        )

        self.assertEqual(set(LIQUIDITY_TYPES), {"bank", "cash", "credit"})
        self.assertEqual(set(DOCUMENT_TYPES), {"sale", "purchase"})
        self.assertEqual(set(CASH_DIFFERENCE_TYPES), {"bank", "cash"})
        self.assertEqual(
            set(JOURNAL_TYPES),
            set(dict(self.env["account.journal"]._fields["type"].selection)),
            "every selectable type needs an entry, or its code prefix and label are gone",
        )

    def test_an_unknown_type_label_degrades_instead_of_raising(self):
        journal = self.env["account.journal"]
        self.assertEqual(journal._get_type_label("sale"), "Customer Invoices")
        self.assertEqual(journal._get_type_label("not_a_type"), "not_a_type")

    def test_a_generated_code_is_recognised_per_prefix(self):
        journal = self.env["account.journal"]
        for code, expected in [
            ("INV1", True),
            ("MISC", True),
            ("BNK12", True),
            (False, True),
            ("ZZ9", False),
            ("INVX", False),
        ]:
            with self.subTest(code=code):
                self.assertIs(journal._is_generated_code(code), expected)


@tagged("post_install", "-at_install")
class TestAccountJournalStructuralAccounts(AccountTestInvoicingCommon):
    def test_a_journals_own_accounts_are_always_allowed(self):
        journal = self.env["account.journal"].create(
            {"name": "Structural", "type": "bank", "code": "TSA1"}
        )
        self.env.flush_all()
        own = journal.default_account_id
        self.assertIn(own, journal.structural_account_ids)

        other = self.env["account.account"].search([("id", "!=", own.id)], limit=1)
        self.assertTrue(
            journal._is_account_allowed(other), "no whitelist means no restriction"
        )

        journal.allowed_account_ids = [Command.set(other.ids)]
        self.env.flush_all()
        self.assertTrue(journal._is_account_allowed(other))
        self.assertTrue(
            journal._is_account_allowed(own),
            "a whitelist that omits the journal's own account must not lock it out",
        )
        unrelated = self.env["account.account"].search(
            [("id", "not in", (own | other).ids)], limit=1
        )
        self.assertFalse(journal._is_account_allowed(unrelated))

    def test_the_structural_set_follows_the_accounts_it_is_built_from(self):
        journal = self.env["account.journal"].create(
            {"name": "Structural 2", "type": "bank", "code": "TSA2"}
        )
        self.env.flush_all()
        before = journal.structural_account_ids
        loss = self.env["account.account"].search(
            [("account_type", "=", "expense"), ("id", "not in", before.ids)], limit=1
        )
        journal.loss_account_id = loss
        self.assertIn(
            loss,
            journal.structural_account_ids,
            "the computed set must invalidate when one of its sources changes",
        )


@tagged("post_install", "-at_install")
class TestAccountJournalNotifications(AccountTestInvoicingCommon):
    def _bill(self, journal):
        return self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "journal_id": journal.id,
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-01-01",
                "invoice_line_ids": [
                    Command.create({"name": "x", "quantity": 1, "price_unit": 10})
                ],
            }
        )

    def test_arriving_einvoices_notify_the_journals_subscribers(self):
        journal = self.company_data["default_journal_purchase"]
        journal.incoming_einvoice_notification_email = "a@example.com, b@example.com"
        moves = self._bill(journal) | self._bill(journal)
        self.env.flush_all()

        before = self.env["mail.mail"].search_count([])
        journal._notify_einvoices_received(moves)
        self.env.flush_all()
        self.assertEqual(
            self.env["mail.mail"].search_count([]) - before,
            4,
            "one mail per invoice per subscriber",
        )

    def test_no_subscribers_means_no_mail(self):
        journal = self.company_data["default_journal_purchase"]
        journal.incoming_einvoice_notification_email = False
        moves = self._bill(journal)
        self.env.flush_all()
        before = self.env["mail.mail"].search_count([])
        journal._notify_einvoices_received(moves)
        self.env.flush_all()
        self.assertEqual(self.env["mail.mail"].search_count([]) - before, 0)


@tagged("post_install", "-at_install")
class TestAccountJournalDefaultAccountHook(AccountTestInvoicingCommon):
    def test_the_localisation_hook_is_told_the_type_on_a_type_change(self):
        journal = self.env["account.journal"].create(
            {"name": "Switcher", "type": "general", "code": "THK1"}
        )
        self.env.flush_all()

        seen = []
        model = type(self.env["account.journal"])
        original = model._prepare_liquidity_account_vals

        def spy(records, company, code, vals):
            seen.append(dict(vals))
            return original(records, company, code, vals)

        self.patch(model, "_prepare_liquidity_account_vals", spy)
        journal.write({"type": "bank"})
        self.env.flush_all()

        self.assertTrue(seen, "a bank journal must build a default account")
        self.assertEqual(seen[0].get("type"), "bank")


@tagged("post_install", "-at_install")
class TestAccountJournalInvalidation(AccountTestInvoicingCommon):
    def test_has_invalid_statements_follows_its_statements(self):
        journal = self.company_data["default_journal_bank"]
        statement = self.env["account.bank.statement"].create(
            {
                "name": "st",
                "line_ids": [
                    Command.create(
                        {
                            "journal_id": journal.id,
                            "payment_ref": "line",
                            "amount": 10.0,
                            "date": fields.Date.today(),
                        }
                    )
                ],
            }
        )
        statement.balance_end_real = statement.balance_end + 100
        self.env.flush_all()
        self.assertTrue(journal.has_invalid_statements)

        statement.balance_end_real = statement.balance_end
        self.env.flush_all()
        self.assertFalse(
            journal.has_invalid_statements,
            "the flag must not survive the statement becoming valid again",
        )

    def test_accounting_date_follows_the_lock_date(self):
        journal = self.company_data["default_journal_misc"]
        move_date = fields.Date.to_date("2026-03-15")
        before = journal.with_context(move_date=move_date).accounting_date
        self.env.company.fiscalyear_lock_date = fields.Date.to_date("2026-06-30")
        self.env.flush_all()
        self.assertNotEqual(
            journal.with_context(move_date=move_date).accounting_date,
            before,
            "a lock-date change must invalidate the cached accounting date",
        )

    def test_an_archived_journal_keeps_its_bank_account(self):
        first = self.env["account.journal"].create(
            {
                "name": "First",
                "type": "bank",
                "code": "TIA1",
                "bank_acc_number": "TESTACC0001",
            }
        )
        bank_account = first.bank_account_id
        second = self.env["account.journal"].create(
            {"name": "Second", "type": "bank", "code": "TIA2"}
        )
        second.write({"bank_account_id": bank_account.id})
        second.write({"active": False})
        self.env.flush_all()

        first.unlink()
        self.env.flush_all()
        bank_account.invalidate_recordset()
        self.assertTrue(
            bank_account.active,
            "a bank account still referenced by an archived journal must stay active",
        )

    def test_unsubscribing_keeps_the_remaining_addresses_in_order(self):
        journal = self.env["account.journal"].create(
            {
                "name": "Notified",
                "type": "sale",
                "code": "TIB1",
                "incoming_einvoice_notification_email": "a@x.com, b@x.com, c@x.com, d@x.com",
            }
        )
        journal._unsubscribe_invoice_notification_email("b@x.com")
        self.assertEqual(
            journal.incoming_einvoice_notification_email, "a@x.com, c@x.com, d@x.com"
        )
