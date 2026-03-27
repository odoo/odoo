# -*- coding: utf-8 -*-

from ast import literal_eval
from unittest.mock import patch

from odoo import http
from odoo.tools import hash_sign
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account.models.account_payment_method import AccountPaymentMethod
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import Form, tagged, HttpCase, new_test_user
from odoo.addons.test_mail.data.test_mail_data import MAIL_EML_ATTACHMENT
from odoo.exceptions import UserError, ValidationError
from odoo import fields, Command


@tagged('post_install', '-at_install')
class TestAccountJournal(AccountTestInvoicingCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency('EUR')
        cls.company_data_2 = cls.setup_other_company()

    def test_constraint_currency_consistency_with_accounts(self):
        ''' The accounts linked to a bank/cash journal must share the same foreign currency
        if specified.
        '''
        journal_bank = self.company_data['default_journal_bank']
        journal_bank.currency_id = self.other_currency

        # Try to set a different currency on the 'debit' account.
        with self.assertRaises(ValidationError):
            journal_bank.default_account_id.currency_id = self.company_data['currency']

    def test_euro_payment_reference_generation(self):
        """
        Test the generation of European (ISO 11649) payment references to ensure
        it correctly handles various journal short codes.
        """
        journal = self.company_data['default_journal_sale']
        journal.invoice_reference_model = 'euro'

        # Case 1: Code contains alphanumeric value.
        journal.code = 'INV'
        invoice_valid = self.init_invoice("out_invoice", products=self.product_a)
        invoice_valid.journal_id = journal
        invoice_valid.action_post()
        self.assertTrue(invoice_valid.payment_reference, "A payment reference should be generated.")
        self.assertIn('INV', invoice_valid.payment_reference, "The reference should be based on the journal code.")

        # Case 2: Code contains a hyphen.
        journal.code = 'INV-'
        invoice_invalid = self.init_invoice("out_invoice", products=self.product_a)
        invoice_invalid.journal_id = journal
        invoice_invalid.action_post()
        self.assertTrue(invoice_invalid.payment_reference, "A payment reference should be generated.")
        self.assertIn(str(journal.id), invoice_invalid.payment_reference, "The reference should fall back to using the journal ID.")

        # Case 3: Code is non-ASCII but alphanumeric (e.g., Greek letter 'INVα'). # noqa: RUF003
        journal.code = 'INVα'
        invoice_unicode = self.init_invoice("out_invoice", products=self.product_a)
        invoice_unicode.journal_id = journal
        invoice_unicode.action_post()
        self.assertTrue(invoice_unicode.payment_reference, "A payment reference should be generated.")
        self.assertIn(str(journal.id), invoice_unicode.payment_reference, "The reference should fall back to using the journal ID for non-ASCII codes.")

    def test_changing_journal_company(self):
        ''' Ensure you can't change the company of an account.journal if there are some journal entries '''

        self.company_data['default_journal_sale'].code = "DIFFERENT"
        self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
        })

        with self.assertRaisesRegex(UserError, "entries linked to it"):
            self.company_data['default_journal_sale'].company_id = self.company_data_2['company']

    def test_account_journal_add_new_payment_method_multi(self):
        """
        Test the automatic creation of payment method lines with the mode set to multi
        """
        Method_get_payment_method_information = AccountPaymentMethod._get_payment_method_information

        def _get_payment_method_information(self):
            res = Method_get_payment_method_information(self)
            res['multi'] = {'mode': 'multi', 'type': ('bank',)}
            return res

        with patch.object(AccountPaymentMethod, '_get_payment_method_information', _get_payment_method_information):
            self.env['account.payment.method'].sudo().create({
                'name': 'Multi method',
                'code': 'multi',
                'payment_type': 'inbound'
            })

        bank_journals_count = self.env['account.journal'].search_count([('type', '=', 'bank')])
        edited_journals_count = self.env['account.journal'].search_count([('inbound_payment_method_line_ids.code', '=', 'multi')])

        # The bank journals have been set
        self.assertEqual(bank_journals_count, edited_journals_count)

    def test_remove_payment_method_lines(self):
        """
        Payment method lines are a bit special in the way their removal is handled.
        If they are linked to a payment at the moment of the deletion, they won't be deleted but the journal_id will be
        set to False.
        If they are not linked to any payment, they will be deleted as expected.
        """

        # Linked to a payment. It will not be deleted, but its journal_id will be set to False.
        first_method = self.inbound_payment_method_line
        self.env['account.payment'].create({
            'amount': 100.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'payment_method_line_id': first_method.id,
        })

        first_method.unlink()

        self.assertFalse(first_method.journal_id)

        # Not linked to anything. It will be deleted.
        second_method = self.outbound_payment_method_line
        second_method.unlink()

        self.assertFalse(second_method.exists())

    def test_account_journal_duplicates(self):
        new_journals = self.env["account.journal"].with_context(import_file=True).create([
            {"name": "OD_BLABLA"},
            {"name": "OD_BLABLU"},
        ])

        self.assertEqual(sorted(new_journals.mapped("code")), ["MISC1", "OD_BL"], "The journals should be set correctly")

    def test_archive_used_journal(self):
        journal = self.env['account.journal'].create({
            'name': 'Test Journal',
            'type': 'sale',
            'code': 'A',
        })
        check_method = self.env['account.payment.method'].sudo().create({
                'name': 'Test',
                'code': 'check_printing_expense_test',
                'payment_type': 'outbound',
        })
        self.env['account.payment.method.line'].create({
            'name': 'Check',
            'payment_method_id': check_method.id,
            'journal_id': journal.id
            })
        journal.action_archive()
        self.assertFalse(journal.active)

    def test_archive_multiple_journals(self):
        journals = self.env['account.journal'].create([{
                'name': 'Test Journal 1',
                'type': 'sale',
                'code': 'A1'
            }, {
                'name': 'Test Journal 2',
                'type': 'sale',
                'code': 'A2'
            }])

        # Archive the Journals
        journals.action_archive()
        self.assertFalse(journals[0].active)
        self.assertFalse(journals[1].active)

        # Unarchive the Journals
        journals.action_unarchive()
        self.assertTrue(journals[0].active)
        self.assertTrue(journals[1].active)

    def test_journal_notifications_unsubscribe(self):
        journal = self.company_data['default_journal_purchase']
        journal.incoming_einvoice_notification_email = 'test@example.com'

        self.authenticate(self.env.user.login, self.env.user.login)
        res = self.url_open(
            f'/my/journal/{journal.id}/unsubscribe',
            data={'csrf_token': http.Request.csrf_token(self)},
            method='POST',
        )
        res.raise_for_status()

        self.assertFalse(journal.incoming_einvoice_notification_email)

    def test_journal_notifications_unsubscribe_success(self):
        journal = self.company_data['default_journal_purchase']
        email = 'test@example.com'
        journal.incoming_einvoice_notification_email = email

        self.authenticate(None, None)
        token = hash_sign(
            self.env,
            journal._get_journal_notification_unsubscribe_scope(),
            {'email_to_unsubscribe': email, 'journal_id': journal.id},
        )

        res = self.url_open(
            f'/my/journal/{journal.id}/unsubscribe?token={token}',
            data={'csrf_token': http.Request.csrf_token(self)},
            method='POST',
        )
        res.raise_for_status()

        self.assertFalse(journal.incoming_einvoice_notification_email)

    def test_journal_notifications_unsubscribe_errors(self):
        journal = self.company_data['default_journal_purchase']
        email = 'test@example.com'
        self.authenticate(None, None)
        valid_token = hash_sign(
            self.env(su=True),
            journal._get_journal_notification_unsubscribe_scope(),
            {'email_to_unsubscribe': email, 'journal_id': journal.id},
        )

        def _get_token():
            return

        def _unsubscribe(token, journal_id=journal.id):
            return self.url_open(
                f'/my/journal/{journal_id}/unsubscribe?token={token}',
                data={'csrf_token': http.Request.csrf_token(self)},
                method='POST',
            )

        with self.subTest('invalid_token'):
            journal.incoming_einvoice_notification_email = email
            res = _unsubscribe('invalid_token')
            self.assertEqual(res.status_code, 403)
            self.assertEqual(journal.incoming_einvoice_notification_email, email)

        with self.subTest('already_unsubscribed'):
            journal.incoming_einvoice_notification_email = email
            first_unsubscribe = _unsubscribe(valid_token)
            first_unsubscribe.raise_for_status()
            self.assertFalse(journal.incoming_einvoice_notification_email)
            second_unsubscribe = _unsubscribe(valid_token)
            self.assertEqual(second_unsubscribe.status_code, 404)

        with self.subTest('wrong_journal_id'):
            journal.incoming_einvoice_notification_email = email
            res = _unsubscribe(valid_token, journal_id=journal.id + 1)
            self.assertEqual(res.status_code, 403)
            self.assertEqual(journal.incoming_einvoice_notification_email, email)


@tagged('post_install', '-at_install', 'mail_alias')
class TestAccountJournalAlias(AccountTestInvoicingCommon, MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()

    def test_alias_name_creation(self):
        """ Test alias creation, notably avoid raising constraints due to ascii
        characters removal. See odoo/odoo@339cdffb68f91eb1455d447d1bdd7133c68723bd """
        # check base test data
        journal1 = self.company_data['default_journal_purchase']
        company1 = journal1.company_id
        journal2 = self.company_data_2['default_journal_sale']
        company2 = journal2.company_id
        # have a non ascii company name
        company2.name = 'ぁ'

        for (aname, jname, jcode, jtype, jcompany), expected_alias_name in zip(
            [
                ('youpie', 'Journal Name', 'NEW1', 'purchase', company1),
                (False, 'Journal Other Name', 'NEW2', 'purchase', company1),
                (False, 'ぁ', 'NEW3', 'purchase', company1),
                (False, 'ぁ', 'ぁ', 'purchase', company1),
                ('youpie', 'Journal Name', 'NEW1', 'purchase', company2),
                (False, 'Journal Other Name', 'NEW2', 'purchase', company2),
                (False, 'ぁ', 'NEW3', 'purchase', company2),
                (False, 'ぁ', 'ぁ', 'purchase', company2),
            ],
            [
                f'youpie-{company1.name}',
                f'journal-other-name-{company1.name}',
                f'new3-{company1.name}',
                f'purchase-{company1.name}',
                f'youpie-{company2.id}',
                f'journal-other-name-{company2.id}',
                f'new3-{company2.id}',
                f'purchase-{company2.id}',
            ]
        ):
            with self.subTest(aname=aname, jname=jname, jcode=jcode, jtype=jtype, jcompany=jcompany):
                new_journal = self.env['account.journal'].create({
                    'code': jcode,
                    'company_id': jcompany.id,
                    'name': jname,
                    'type': jtype,
                    # force alias_name only if given, to check default value otherwise
                    **({'alias_name': aname} if aname else {}),
                })
                self.assertEqual(new_journal.alias_name, expected_alias_name)

        # other types: no mail support by default
        journals = self.env['account.journal'].create([{
            'code': f'NEW{jtype}',
            'name': f'Type {jtype}',
            'type': jtype}
            for jtype in ('general', 'cash', 'bank')
        ])
        self.assertFalse(journals.alias_id, 'Do not create useless aliases')
        self.assertFalse(list(filter(None, journals.mapped('alias_name'))))

    def test_alias_name_form(self):
        """ Test alias name update using Form tool (onchange) """
        journal = Form(self.env['account.journal'])
        journal.name = 'Test With Form'
        self.assertFalse(journal.alias_name)
        journal.type = 'sale'
        self.assertEqual(journal.alias_name, f'test-with-form-{self.env.company.name}')
        journal.type = 'cash'
        self.assertFalse(journal.alias_name)

    def test_alias_from_type(self):
        """ Test alias behavior on journal, especially alias_name management as
        well as defaults update, see odoo/odoo@400b6860271a11b9914166ff7e42939c4c6192dc """
        journal = self.company_data['default_journal_purchase']

        # assert base test data
        company_name = 'company_1_data'
        journal_code = 'BILL'
        journal_name = 'Purchases'
        journal_alias = journal.alias_id
        self.assertEqual(journal.code, journal_code)
        self.assertEqual(journal.company_id.name, company_name)
        self.assertEqual(journal.name, journal_name)
        self.assertEqual(journal.type, 'purchase')

        # assert default creation data
        self.assertEqual(journal_alias.alias_contact, 'everyone')
        self.assertDictEqual(
            dict(literal_eval(journal_alias.alias_defaults)),
            {
                'move_type': 'in_invoice',
                'company_id': journal.company_id.id,
                'journal_id': journal.id,
            }
        )
        self.assertFalse(journal_alias.alias_force_thread_id, 'Journal alias should create new moves')
        self.assertEqual(journal_alias.alias_model_id, self.env['ir.model']._get('account.move'),
                         'Journal alias targets moves')
        self.assertEqual(journal_alias.alias_name, f'purchases-{company_name}')
        self.assertEqual(journal_alias.alias_parent_model_id, self.env['ir.model']._get('account.journal'),
                         'Journal alias owned by journal itself')
        self.assertEqual(journal_alias.alias_parent_thread_id, journal.id,
                         'Journal alias owned by journal itself')

        # update alias_name, ensure a fallback on a real name when not explicit reset
        for alias_name, expected in [
            (False, False),
            ('', False),
            (' ', f'purchases-{company_name}'),  # error recuperation
            ('.', f'purchases-{company_name}'),  # error recuperation
            ('😊', f'purchases-{company_name}'),  # resets, unicode not supported
            ('ぁ', f'purchases-{company_name}'),  # resets, non ascii not supported
            ('Youpie Boum', 'youpie-boum'),
        ]:
            with self.subTest(alias_name=alias_name):
                journal.write({'alias_name': alias_name})
                self.assertEqual(journal.alias_name, expected)
                self.assertEqual(journal_alias.alias_name, expected)

        # changing type should void if not purchase or sale
        for jtype in ('general', 'cash', 'bank'):
            journal.write({'type': jtype})
            self.assertEqual(journal.alias_id, journal_alias,
                             'Dà not unlink aliases, just reset their value')
            self.assertFalse(journal.alias_name)
            self.assertFalse(journal_alias.alias_name)

        # changing type should reset if sale or purchase
        journal.company_id.write({'name': 'New Company Name'})
        journal.write({'name': 'Reset Journal', 'type': 'sale'})
        journal_alias_2 = journal.alias_id
        self.assertEqual(journal_alias_2.alias_contact, 'everyone')
        self.assertDictEqual(
            dict(literal_eval(journal_alias_2.alias_defaults)),
            {
                'move_type': 'out_invoice',
                'company_id': journal.company_id.id,
                'journal_id': journal.id,
            }
        )
        self.assertFalse(journal_alias_2.alias_force_thread_id, 'Journal alias should create new moves')
        self.assertEqual(journal_alias_2.alias_model_id, self.env['ir.model']._get('account.move'),
                         'Journal alias targets moves')
        self.assertEqual(journal_alias_2.alias_name, 'reset-journal-new-company-name')
        self.assertEqual(journal_alias_2.alias_parent_model_id, self.env['ir.model']._get('account.journal'),
                         'Journal alias owned by journal itself')
        self.assertEqual(journal_alias_2.alias_parent_thread_id, journal.id,
                         'Journal alias owned by journal itself')

    def test_alias_create_unique(self):
        """ Make auto-generated alias_name unique when needed """
        company_name = self.company_data['company'].name
        journal = self.env['account.journal'].create({
            'name': 'Test Journal',
            'type': 'sale',
            'code': 'A',
        })
        journal2 = self.env['account.journal'].create({
            'name': 'Test Journal',
            'type': 'sale',
            'code': 'B',
        })
        self.assertEqual(journal.alias_name, f'test-journal-{company_name}')
        self.assertEqual(journal2.alias_name, f'test-journal-{company_name}-b')

    def test_non_latin_journal_code_payment_reference(self):
        """ Ensure non-Latin journal codes do not cause errors and payment references are valid """
        non_latin_code = 'TΠY'
        latin_code = 'TPY'

        journal_non_latin = self.env['account.journal'].create({
            'name': 'Test Journal',
            'type': 'sale',
            'code': non_latin_code,
            'invoice_reference_model': 'euro'
        })
        journal_latin = self.env['account.journal'].create({
            'name': 'Test Journal',
            'type': 'sale',
            'code': latin_code,
            'invoice_reference_model': 'euro'
        })

        invoice_non_latin = self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            invoice_date=fields.Date.today(),
            post=True,
            products=[self.product_a],
            journal=journal_non_latin,
        )
        invoice_latin = self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            invoice_date=fields.Date.today(),
            post=True,
            products=[self.product_a],
            journal=journal_latin,
        )

        expected_id = str(invoice_non_latin.journal_id.id)
        ref_parts_non_latin = invoice_non_latin.payment_reference.split()
        self.assertEqual(ref_parts_non_latin[1][:len(expected_id)], expected_id, "The reference should start with " + expected_id)

        ref_parts_latin = invoice_latin.payment_reference.split()
        self.assertIn(ref_parts_latin[1][:3], latin_code, f"Expected journal code '{latin_code}' in second part of reference")

    def test_use_default_account_from_journal(self):
        """
        Test that the autobalance uses the default account id of the journal
        """
        autobalance_account = self.env['account.account'].create({
            'name': 'Autobalance Account',
            'account_type': 'income',
            'code': 'A',
        })
        journal = self.env['account.journal'].create({
            'name': 'Test Journal',
            'type': 'general',
            'code': 'B',
            'default_account_id': autobalance_account.id,
        })

        entry = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'line_ids': [
                Command.create({
                    'debit': 100.0,
                    'credit': 0.0,
                    'tax_ids': (self.company_data['default_tax_sale']),
                    'account_id': self.company_data['default_account_revenue'].id
                })
            ]
        })

        entry.action_post()
        self.assertRecordValues(entry.line_ids, [
            {'balance': 100.0, 'account_id': self.company_data['default_account_revenue'].id},
            {'balance': 15.0, 'account_id': self.company_data['default_account_tax_sale'].id},
            {'balance': -115.0, 'account_id': autobalance_account.id},
        ])

    def test_send_email_to_alias_from_other_company(self):
        user_company_2 = new_test_user(
            self.env,
            name='company 2 user',
            login='company_2_user',
            password='company_2_user',
            email='company_2_user@test.com',
            company_id=self.company_data_2['company'].id
        )
        self.format_and_process(
            MAIL_EML_ATTACHMENT,
            user_company_2.email,
            self.company_data['default_journal_purchase'].alias_email,
            subject='purchase test mail',
            target_model='account.move',
            msg_id='<test-account-move-alias-id>',
        )
        self.assertTrue(self.env['account.move'].search([('invoice_source_email', '=', 'company_2_user@test.com')]))

    def test_alias_uniqueness_without_domain(self):
        """Ensure alias_name is unique even if alias_domain is not defined."""
        default_account = self.env['account.account'].search(
            domain=[('account_type', 'in', ('income', 'income_other'))],
            limit=1,
        )
        with Form(self.env['account.journal']) as journal_form:
            journal_form.type = 'sale'
            journal_form.code = 'A'
            journal_form.name = 'Test Journal 1'
            journal_form.default_account_id = default_account
            journal_1 = journal_form.save()
        with Form(self.env['account.journal']) as journal_form:
            journal_form.type = 'sale'
            journal_form.code = 'B'
            journal_form.name = 'Test Journal 2'
            journal_form.default_account_id = default_account
            journal_2 = journal_form.save()
        self.assertNotEqual(journal_1.alias_id.alias_name, journal_2.alias_id.alias_name)

    def test_payment_method_line_accounts_on_recompute(self):
        """
        Test that outstanding payments/receipts accounts are not removed during the computation of the payment method lines
        """
        bank_journal = self.company_data['default_journal_bank']
        outstanding_receipt_account = self.env['account.chart.template'].ref('account_journal_payment_debit_account_id')
        outstanding_payment_account = self.env['account.chart.template'].ref('account_journal_payment_credit_account_id')

        inbound_method_lines = bank_journal.inbound_payment_method_line_ids
        inbound_method_lines_names = inbound_method_lines.mapped('name')
        inbound_method_lines[0].payment_account_id = outstanding_receipt_account

        outbound_method_lines = bank_journal.outbound_payment_method_line_ids
        outbound_method_lines_names = outbound_method_lines.mapped('name')
        outbound_method_lines[0].payment_account_id = outstanding_payment_account
        new_outbound_payment_line = outbound_method_lines[0].copy({'payment_account_id': self.company_data['default_account_deferred_expense'].id})
        bank_journal.outbound_payment_method_line_ids = [Command.link(new_outbound_payment_line.id)]

        # Set currency_id to trigger the compute of {in,out}bound_payment_method_line_ids
        bank_journal.currency_id = self.company_data['currency']

        self.assertRecordValues(bank_journal.inbound_payment_method_line_ids, [
            {
                'name': name,
                'payment_account_id': outstanding_receipt_account.id if index == 0 else False,
            } for index, name in enumerate(inbound_method_lines_names)
        ])
        self.assertRecordValues(bank_journal.outbound_payment_method_line_ids, [
            {
                'name': name,
                'payment_account_id': outstanding_payment_account.id if index == 0 else False,
            } for index, name in enumerate(outbound_method_lines_names)
        ])
