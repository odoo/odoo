# -*- coding: utf-8 -*-
from base64 import b64encode
from contextlib import contextmanager
from freezegun import freeze_time
from unittest.mock import patch

from odoo.tests import Form, tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.addons.account_followup.tests.common import TestAccountFollowupCommon
from odoo.tools.misc import file_open
from odoo import Command, fields


@tagged('post_install', '-at_install')
class TestAccountFollowupReports(TestAccountReportsCommon, TestAccountFollowupCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_a.email = 'partner_a@mypartners.xyz'
        cls.report = cls.env.ref('account_reports.followup_report')

    def test_followup_report(self):
        ''' Test report lines when printing the follow-up report. '''
        # Init options.
        report = self.env['account.followup.report']
        options = {
            'partner_id': self.partner_a.id,
            'multi_currency': True,
        }

        # 2016-01-01: First invoice, partially paid.

        invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 500,
                'tax_ids': [],
            })]
        })
        invoice_1.action_post()

        payment_1 = self.env['account.move'].create({
            # pylint: disable=C0326
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'debit': 0.0,       'credit': 200.0,    'account_id': self.company_data['default_account_receivable'].id}),
                (0, 0, {'debit': 200.0,     'credit': 0.0,      'account_id': self.company_data['default_journal_bank'].default_account_id.id}),
            ],
        })
        payment_1.action_post()

        (payment_1 + invoice_1).line_ids\
            .filtered(lambda line: line.account_id == self.company_data['default_account_receivable'])\
            .reconcile()

        with freeze_time('2016-01-01'):
            self.assertLinesValues(
                # pylint: disable=C0326
                report._get_followup_report_lines(options),
                #   Name                                    Date,           Due Date,       Doc.      Total Due
                [   0,                                      1,              2,              3,        5],
                [
                    ('INV/2016/00001',                      '01/01/2016',   '01/01/2016',   '',       300.0),
                    ('',                                    '',             '',             '',       300.0),
                ],
                options,
            )

        # 2016-01-05: Credit note due at 2016-01-10.

        invoice_2 = self.env['account.move'].create({
            'move_type': 'out_refund',
            'invoice_date': '2016-01-05',
            'invoice_date_due': '2016-01-10',
            'partner_id': self.partner_a.id,
            'invoice_payment_term_id': False,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 200,
                'tax_ids': [],
            })]
        })
        invoice_2.action_post()

        with freeze_time('2016-01-05'):
            self.assertLinesValues(
                # pylint: disable=C0326
                report._get_followup_report_lines(options),
                #   Name                                    Date,           Due Date,       Doc.      Total Due
                [   0,                                      1,              2,              3,        5],
                [
                    ('RINV/2016/00001',                     '01/05/2016',   '01/10/2016',   '',      -200.0),
                    ('INV/2016/00001',                      '01/01/2016',   '01/01/2016',   '',       300.0),
                    ('',                                    '',             '',             '',       100.0),
                    ('',                                    '',             '',             '',       300.0),
                ],
                options,
            )

        # 2016-01-15: Draft invoice + previous credit note reached the date_maturity + first invoice reached the delay
        # of the first followup level.

        self.env['account.move'].create({
            'move_type': 'out_refund',
            'invoice_date': '2016-01-15',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 1000,
                'tax_ids': [],
            })]
        })

        with freeze_time('2016-01-15'):
            self.assertLinesValues(
                # pylint: disable=C0326
                report._get_followup_report_lines(options),
                #   Name                                    Date,           Due Date,       Doc.      Total Due
                [   0,                                      1,              2,              3,        5],
                [
                    ('RINV/2016/00001',                     '01/05/2016',   '01/10/2016',   '',      -200.0),
                    ('INV/2016/00001',                      '01/01/2016',   '01/01/2016',   '',       300.0),
                    ('',                                    '',             '',             '',       100.0),
                    ('',                                    '',             '',             '',       100.0),
                ],
                options,
            )

        # Trigger the followup report notice.

        invoice_attachments = self.env['ir.attachment']
        for invoice in invoice_1 + invoice_2:
            invoice_attachment = self.env['ir.attachment'].create({
                'name': 'some_attachment.pdf',
                'res_id': invoice.id,
                'res_model': 'account.move',
                'res_field': 'invoice_pdf_report_file',  # simulates send & print
                'datas': 'test',
                'type': 'binary',
            })
            invoice_attachments += invoice_attachment
            invoice._message_set_main_attachment_id(invoice_attachment)

        self.partner_a._compute_unpaid_invoices()
        options.update(
            attachment_ids=invoice_attachments.ids,
            email=True,
            manual_followup=True,
            join_invoices=True,
        )
        with patch.object(type(self.env['mail.mail']), 'unlink', lambda self: None):
            with patch.object(self.env.registry['account.report'], 'export_to_pdf', autospec=True, side_effect=lambda *args, **kwargs: {'file_name': 'fake_partner_ledger.pdf', 'file_content': b'', 'file_type': 'pdf'}):
                self.partner_a.execute_followup(options)
        sent_attachments = self.env['mail.message'].search([('partner_ids', '=', self.partner_a.id)]).attachment_ids
        self.assertListEqual(sent_attachments.mapped('name'), [f'{self.partner_a.name} - fake_partner_ledger.pdf', 'some_attachment.pdf', 'some_attachment.pdf'])

        options.update(
            attachment_ids=[],
            email=False,
            join_invoices=False,
        )
        with (
            patch.object(self.env.registry['mail.mail'], 'unlink', lambda self: None),
            patch.object(
                self.env.registry['res.partner'],
                '_get_partner_account_report_attachment',
                autospec=True,
                side_effect=lambda *args, **kwargs: invoice_attachments[0],
            ),
        ):
            self.partner_a.execute_followup(options)
        self.assertEqual(options['attachment_ids'], [invoice_attachments.ids[0]], "The report attachment should be included regardless of join_invoices and email checkboxes.")

        attachaments_domain = [('attachment_ids', '=', attachment.id) for attachment in invoice_attachments]
        mail = self.env['mail.mail'].search([('recipient_ids', '=', self.partner_a.id)] + attachaments_domain)
        self.assertTrue(mail, "A payment reminder email should have been sent.")

    def test_followup_report_journal_option_disabled(self):
        options = {
            'partner_id': self.partner_a.id,
            'manual_followup': True,
        }

        self.report.filter_journals = False
        with patch.object(self.env.registry['account.report'], 'export_to_pdf', autospec=True, side_effect=lambda *args, **kwargs: {'file_name': 'fake_partner_ledger.pdf', 'file_content': b'', 'file_type': 'pdf'}):
            self.partner_a.execute_followup(options)

    def test_followup_lines_branches(self):
        branch = self.env['res.company'].create({
            'name': 'branch',
            'parent_id': self.env.company.id
        })
        self.cr.precommit.run()  # load the COA

        report = self.env['account.followup.report']
        options = {
            'partner_id': self.partner_a.id,
        }

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'company_id': branch.id,
            'invoice_payment_term_id': self.pay_terms_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 500,
                'tax_ids': [],
            })]
        })
        invoice.action_post()

        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_followup_report_lines(options),
            #   Name                                    Date,           Due Date,       Doc.      Total Due
            [   0,                                      1,              2,              3,        5],
            [
                ('INV/2016/00001',                      '01/01/2016',   '01/01/2016',   '',       '$\xa0500.00'),
                ('',                                    '',             '',             '',       '$\xa0500.00'),
                ('',                                    '',             '',             '',       '$\xa0500.00'),
            ],
            options,
        )

    def test_followup_report_address_1(self):
        ''' Test child contact priorities: the company will be used when there is no followup or billing contacts
        '''

        Partner = self.env['res.partner']
        self.partner_a.is_company = True
        options = {
            'partner_id': self.partner_a.id,
        }

        child_partner = Partner.create({
            'name': "Child contact",
            'type': "contact",
            'parent_id': self.partner_a.id,
        })

        mail = self.env['mail.mail'].search([('recipient_ids', '=', self.partner_a.id)])
        self.init_invoice('out_invoice', partner=child_partner, invoice_date='2016-01-01', amounts=[500], post=True)
        self.partner_a._compute_unpaid_invoices()
        with patch.object(type(self.env['mail.mail']), 'unlink', lambda self: None):
            with patch.object(self.env.registry['account.report'], 'export_to_pdf', autospec=True, side_effect=lambda *args, **kwargs: {'file_name': 'fake_partner_ledger.pdf', 'file_content': b'', 'file_type': 'pdf'}):
                self.env['account.followup.report']._send_email(options)

        mail = self.env['mail.mail'].search([('recipient_ids', '=', self.partner_a.id)])
        self.assertTrue(mail, "The payment reminder email should have been sent to the company.")

    def test_followup_report_address_2(self):
        ''' Test child contact priorities: the follow up contact will be preferred over the billing contact
        '''

        Partner = self.env['res.partner']
        self.partner_a.is_company = True
        options = {
            'partner_id': self.partner_a.id,
        }

        # Testing followup sent to billing address if used in invoice

        child_partner = Partner.create({
            'name': "Child contact",
            'type': "contact",
            'parent_id': self.partner_a.id,
        })
        invoice_partner = Partner.create({
            'name' : "Child contact invoice",
            'type' : "invoice",
            'email' : "test-invoice@example.com",
            'parent_id': child_partner.id,
        })

        self.init_invoice('out_invoice', partner=invoice_partner, invoice_date='2016-01-01', amounts=[500], post=True)

        self.partner_a._compute_unpaid_invoices()
        with patch.object(type(self.env['mail.mail']), 'unlink', lambda self: None):
            with patch.object(self.env.registry['account.report'], 'export_to_pdf', autospec=True, side_effect=lambda *args, **kwargs: {'file_name': 'fake_partner_ledger.pdf', 'file_content': b'', 'file_type': 'pdf'}):
                self.env['account.followup.report']._send_email(options)

        mail = self.env['mail.mail'].search([('recipient_ids', '=', invoice_partner.id)])
        self.assertTrue(mail, "The payment reminder email should have been sent to the invoice partner.")
        mail.unlink()

        # Testing followup partner priority

        followup_partner = Partner.create({
            'name' : "Child contact followup",
            'type' : "followup",
            'email' : "test-followup@example.com",
            'parent_id': self.partner_a.id,
        })

        self.partner_a._compute_unpaid_invoices()
        with patch.object(type(self.env['mail.mail']), 'unlink', lambda self: None):
            with patch.object(self.env.registry['account.report'], 'export_to_pdf', autospec=True, side_effect=lambda *args, **kwargs: {'file_name': 'fake_partner_ledger.pdf', 'file_content': b'', 'file_type': 'pdf'}):
                self.env['account.followup.report']._send_email(options)

        mail = self.env['mail.mail'].search([('recipient_ids', '=', followup_partner.id)])
        self.assertTrue(mail, "The payment reminder email should have been sent to the followup partner.")

    def test_followup_invoice_no_amount(self):
        # Init options.
        report = self.env['account.followup.report']
        options = {
            'partner_id': self.partner_a.id,
        }

        invoice_move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2022-01-01',
            'invoice_line_ids': [
                (0, 0, {'quantity': 0, 'price_unit': 30}),
            ],
        })
        invoice_move.action_post()

        lines = report._get_followup_report_lines(options)
        self.assertEqual(len(lines), 0, "There should be no line displayed")

    def test_negative_followup_report(self):
        ''' Test negative or null followup reports: if a contact has an overdue invoice but has a negative of null total due, no action is needed.
        '''
        followup_line = self.env['account_followup.followup.line'].create({
            'company_id': self.env.company.id,
            'name': 'First Reminder',
            'delay': 15,
            'send_email': False,
        })
        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 500,
                'tax_ids': [],
            })]
        }).action_post()

        self.env['account.move'].create({
            'move_type': 'out_refund',
            'invoice_date': '2016-01-15',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 300,
                'tax_ids': [],
            })]
        }).action_post()
        self.assertEqual(self.partner_a.total_due, 200)
        self.assertPartnerFollowup(self.partner_a, 'in_need_of_action', followup_line)

        self.env['account.payment'].create({
            'partner_id': self.partner_a.id,
            'amount': 400,
        }).action_post()
        self.assertEqual(self.partner_a.total_due, -200)
        self.assertPartnerFollowup(self.partner_a, 'no_action_needed', followup_line)

    def test_followup_report_style(self):
        """
            This report is often broken in terms of styling, this test will check the styling of the lines.
            (This test will not work if we modify the template it self)
        """
        report = self.env['account.followup.report']
        options = {
            'partner_id': self.partner_a.id,
            'multi_currency': True,
        }

        # 2016-01-01: First invoice, partially paid.

        invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 500,
                'tax_ids': [],
            })]
        })
        invoice_1.action_post()

        payment_1 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create({
                    'debit': 0.0,
                    'credit': 200.0,
                    'account_id': self.company_data['default_account_receivable'].id
                }),
                Command.create({
                    'debit': 200.0,
                    'credit': 0.0,
                    'account_id': self.company_data['default_journal_bank'].default_account_id.id
                }),
            ],
        })
        payment_1.action_post()

        (payment_1 + invoice_1).line_ids \
            .filtered(lambda line: line.account_id == self.company_data['default_account_receivable']) \
            .reconcile()

        lines = report._get_followup_report_lines(options)
        # The variable lines is composed of 3 lines, the line of the move and two lines of total (due and overdue)
        # First line
        line_0_style = [
            'white-space:nowrap;text-align:left;',
            'white-space:nowrap;text-align:left;color: red;',
            'text-align:center; white-space:normal;',
            'text-align:left; white-space:normal;',
            'text-align:right; white-space:normal;',
        ]
        for expected_style, column in zip(line_0_style, lines[0]['columns']):
            self.assertEqual(expected_style, column['style'])

        # Second line
        self.assertEqual(lines[1]['columns'][3].get('style'), 'text-align:right; white-space:normal; font-weight: bold;') # Total due title
        self.assertEqual(lines[1]['columns'][4].get('style'), 'text-align:right; white-space:normal; font-weight: bold;') # Total due value

        # Third line
        self.assertEqual(lines[2]['columns'][3].get('style'), 'text-align:right; white-space:normal; font-weight: bold;')  # Total overdue title
        self.assertEqual(lines[2]['columns'][4].get('style'), 'text-align:right; white-space:normal; font-weight: bold;')  # Total overdue value

        # Check template used
        for line in lines:
            for column in line['columns']:
                self.assertEqual(column['template'], 'account_followup.line_template')

    def test_followup_send_email(self):
        """ Tests that the email address in the mail.template is used to send the followup email."""
        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 500,
                'tax_ids': [],
            })]
        }).action_post()

        @contextmanager
        def create_and_send_email(email_from, subject):
            """ Create a mail.template, open the followup wizard and send the followup email."""
            mail_template = self.env['mail.template'].create({
                'name': "Payment Reminder",
                'model_id': self.env.ref('base.model_res_partner').id,
                'email_from': email_from,
                'partner_to': '{{ object.id }}',
                'subject': subject,
            })
            wizard = self.env['account_followup.manual_reminder'].with_context(
                active_model='res.partner',
                active_ids=self.partner_a.ids,
            ).create({})
            wizard.email = True  # tick the 'email' checkbox
            wizard.template_id = mail_template
            with patch.object(self.env.registry['account.report'], 'export_to_pdf', autospec=True, side_effect=lambda *args, **kwargs: {'file_name': 'fake_partner_ledger.pdf', 'file_content': b'', 'file_type': 'pdf'}):
                wizard.process_followup()
            yield
            self.assertEqual(len(message), 1)
            self.assertEqual(message.author_id, self.env.user.partner_id)

        # case 1: the email_from is dynamically set
        with create_and_send_email(
            email_from="{{ object._get_followup_responsible().email_formatted }}",
            subject="{{ (object.company_id or object._get_followup_responsible().company_id).name }} Pay me now !",
        ):
            message = self.env['mail.message'].search([('subject', 'like', "Pay me now !")])
            self.assertEqual(message.email_from, self.env.user.partner_id.email_formatted)

        # case 2: the email_from is hardcoded in the template
        with create_and_send_email(
            email_from="test@odoo.com",
            subject="{{ (object.company_id or object._get_followup_responsible().company_id).name }} Pay me noooow !",
        ):
            message = self.env['mail.message'].search([('subject', 'like', "Pay me noooow !")])
            self.assertEqual(message.email_from, "test@odoo.com")

    def test_process_automatic_followup_send_email(self):
        """ Tests that the email address in the mail.template is used to send the followup email from the cron."""
        self.env['account_followup.followup.line'].create({
            'company_id': self.env.company.id,
            'name': 'First Reminder',
            'delay': 15,
            'send_email': True,
        })
        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 500,
                'tax_ids': [],
            })]
        }).action_post()

        @contextmanager
        def create_and_send_email(email_from, subject):
            """ Create a mail.template, link it with the followup line and execute followups."""
            mail_template = self.env['mail.template'].create({
                'name': "Payment Reminder",
                'model_id': self.env.ref('base.model_res_partner').id,
                'email_from': email_from,
                'partner_to': '{{ object.id }}',
                'subject': subject,
            })
            self.partner_a.followup_line_id.mail_template_id = mail_template
            self.partner_a.followup_next_action_date = False
            with patch.object(self.env.registry['account.report'], 'export_to_pdf', autospec=True, side_effect=lambda *args, **kwargs: {'file_name': 'fake_partner_ledger.pdf', 'file_content': b'', 'file_type': 'pdf'}):
                self.partner_a._execute_followup_partner(options={'snailmail': False})
            yield
            self.assertEqual(len(message), 1)
            self.assertEqual(message.author_id, self.partner_a._get_followup_responsible().partner_id, "Automatic followups should have the followup responsible as the author.")

        # case 1: the email_from is dynamically set
        with create_and_send_email(
            email_from="{{ object._get_followup_responsible().email_formatted }}",
            subject="{{ (object.company_id or object._get_followup_responsible().company_id).name }} Pay me now !",
        ):
            message = self.env['mail.message'].search([('subject', 'like', "Pay me now !")])
            self.assertEqual(message.email_from, self.env.user.partner_id.email_formatted)

        # we have to create a new overdue invoice to test the second case as the previous invoice
        # will no longer trigger the followup
        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 600,
                'tax_ids': [],
            })]
        }).action_post()

        # case 2: the email_from is hardcoded in the template
        with create_and_send_email(
            email_from="test@odoo.com",
            subject="{{ (object.company_id or object._get_followup_responsible().company_id).name }} Pay me noooow !",
        ):
            message = self.env['mail.message'].search([('subject', 'like', "Pay me noooow !")])
            self.assertEqual(message.email_from, "test@odoo.com")

    def test_compute_render_model(self):
        with Form(self.env['account_followup.manual_reminder'].with_context(
            active_model='res.partner',
            active_ids=self.partner_a.ids,
        )) as wizard:
            self.assertEqual(wizard.render_model, "res.partner")

    def test_followup_report_with_levels_on_main_company(self):
        cron = self.env.ref('account_followup.ir_cron_auto_post_draft_entry')

        self.env['account_followup.followup.line'].create([{
            'company_id': self.company_data['company'].id,
            'name': 'First Reminder',
            'delay': 15,
            'send_email': True,
            'auto_execute': True,
        }, {
            'company_id': self.company_data['company'].id,
            'name': 'Second Reminder',
            'delay': 30,
            'send_email': True,
            'auto_execute': True,
        }])

        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'invoice_date_due': '2016-01-01',
            'date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 500,
            })]
        }).action_post()

        with (
            freeze_time('2022-01-10'),
            patch.object(self.env.registry['res.partner'], '_send_followup') as patched,
            patch.object(self.env.registry['ir.actions.report'], '_run_wkhtmltopdf', return_value=b"0")
        ):
            cron.method_direct_trigger()
            # For the same reason we clear the cache in assertPartnerFollowup, to avoid this test change the state of the cache,
            # which could break other tests.
            self.env.cr.cache.pop('res_partner_all_followup', None)
            self.assertEqual(patched.call_count, 1)

        count_mail = self.env['mail.message'].search_count([('record_company_id', '=', self.company_data['company'].id)])
        # We should have 1 email :
        # 1 for the main company
        self.assertEqual(count_mail, 1)

    def test_followup_report_with_levels_on_one_branch(self):
        cron = self.env.ref('account_followup.ir_cron_auto_post_draft_entry')

        branch_a, branch_b = self.env['res.company'].create([{
            'name': 'Branch number 1',
            'parent_id': self.company_data['company'].id,
        }, {
            'name': 'Branch number 2',
            'parent_id': self.company_data['company'].id,
        }])

        self.cr.precommit.run()  # load the COA

        self.env['account_followup.followup.line'].create([{
            'company_id': branch_a.id,
            'name': 'First Reminder (A)',
            'delay': 15,
            'send_email': True,
            'auto_execute': True,
        }, {
            'company_id': branch_a.id,
            'name': 'Second Reminder (A)',
            'delay': 30,
            'send_email': True,
            'auto_execute': True,
        }])

        self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'invoice_date_due': '2016-01-01',
            'date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'company_id': branch_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 400,
            })]
        }, {
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'invoice_date_due': '2016-01-01',
            'date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'company_id': branch_b.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 800,
            })]
        }]).action_post()

        with (
            freeze_time('2022-01-10'),
            patch.object(self.env.registry['res.partner'], '_send_followup') as patched,
            patch.object(self.env.registry['ir.actions.report'], '_run_wkhtmltopdf', return_value=b"0")
        ):
            cron.method_direct_trigger()
            # For the same reason we clear the cache in assertPartnerFollowup, to avoid this test change the state of the cache,
            # which could break other tests.
            self.env.cr.cache.pop('res_partner_all_followup', None)
            self.assertEqual(patched.call_count, 1)

        count_mail = self.env['mail.message'].search_count([('record_company_id', '=', branch_a.id)])
        # We should have 1 email :
        # 1 for the Branch number 1
        self.assertEqual(count_mail, 1)

    def test_followup_report_with_levels_on_branches_and_main_company(self):
        cron = self.env.ref('account_followup.ir_cron_auto_post_draft_entry')

        branch_a, branch_b = self.env['res.company'].create([{
            'name': 'Branch number 1',
            'parent_id': self.company_data['company'].id,
        }, {
            'name': 'Branch number 2',
            'parent_id': self.company_data['company'].id,
        }])

        self.cr.precommit.run()  # load the COA

        self.env['account_followup.followup.line'].create([{
            'company_id': branch_a.id,
            'name': 'First Reminder (A)',
            'delay': 15,
            'send_email': True,
            'auto_execute': True,
        }, {
            'company_id': branch_a.id,
            'name': 'Second Reminder (A)',
            'delay': 30,
            'send_email': True,
            'auto_execute': True,
        }, {
            'company_id': branch_b.id,
            'name': 'First Reminder (B)',
            'delay': 10,
            'send_email': True,
            'auto_execute': True,
        }, {
            'company_id': branch_b.id,
            'name': 'Second Reminder (B)',
            'delay': 20,
            'send_email': True,
            'auto_execute': True,
        }, {
            'company_id': self.company_data['company'].id,
            'name': 'First Reminder',
            'delay': 20,
            'send_email': True,
            'auto_execute': True,
        }, {
            'company_id': self.company_data['company'].id,
            'name': 'Second Reminder',
            'delay': 40,
            'send_email': True,
            'auto_execute': True,
        }])

        self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'invoice_date_due': '2016-01-01',
            'date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'company_id': branch_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 400,
            })]
        }, {
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'invoice_date_due': '2016-01-01',
            'date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'company_id': branch_b.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 800,
            })]
        }, {
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'invoice_date_due': '2016-01-01',
            'date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'company_id': self.company_data['company'].id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 200,
            })]
        }]).action_post()

        with (
            freeze_time('2022-01-10'),
            patch.object(self.env.registry['res.partner'], '_send_followup') as patched,
            patch.object(self.env.registry['ir.actions.report'], '_run_wkhtmltopdf', return_value=b"0")
        ):
            cron.method_direct_trigger()
            # For the same reason we clear the cache in assertPartnerFollowup, to avoid this test change the state of the cache,
            # which could break other tests.
            self.env.cr.cache.pop('res_partner_all_followup', None)
            self.assertEqual(patched.call_count, 3)

        count_mail = self.env['mail.message'].search_count([('record_company_id', 'in', [self.company_data['company'].id, branch_a.id, branch_b.id])])
        # We should have 3 emails :
        # 1 for the main company
        # 1 for the Branch number 1
        # 1 for the Branch number 2
        self.assertEqual(count_mail, 3)

        # Now we check the amounts overdue
        # Expected : 200 (main_company) + 400 (branch_a) + 800 (branch_b)
        self.assertEqual(self.partner_a.total_overdue, 1400)
        # Expected : 400
        self.assertEqual(self.partner_a.with_company(branch_a).total_overdue, 400)
        # Expected : 800
        self.assertEqual(self.partner_a.with_company(branch_b).total_overdue, 800)

    def test_partner_total_due_with_payable(self):
        """
        Test that the total due for a partner also reflects payable accounts and is coherent with the customer statement report.
        """
        # Init options.
        report = self.env.ref('account_reports.customer_statement_report')
        default_options = {
            'partner_id': self.partner_a.id,
            'multi_currency': True,
            'unfold_all': True,
        }
        options = self._generate_options(report, fields.Date.from_string('2016-01-01'), fields.Date.from_string('2016-12-31'), default_options=default_options)

        self.init_invoice('out_invoice', self.partner_a, '2016-01-01', True, amounts=[500])

        self.assertRecordValues(self.partner_a, [{'total_due': 500.0, 'total_all_due': 500.0}])

        with freeze_time('2016-01-01'):
            self.assertLinesValues(
                # pylint: disable=C0326
                report._get_lines(options),
                #   Name                                        Date,        Due Date,  Amount,       Balance
                [   0,                                      1,              2,       3,             5],
                [
                    ('partner_a',                                  '',             '',   500.0,         500.0),
                    ('INV/2016/00001',                   '01/01/2016',   '01/01/2016',   500.0,         500.0),
                    ('Total partner_a',                            '',             '',   500.0,         500.0),
                    ('Total',                                      '',             '',   500.0,         500.0),
                ],
                options,
            )

        self.init_invoice('in_invoice', self.partner_a, '2016-01-01', True, amounts=[200])

        self.assertRecordValues(self.partner_a, [{'total_due': 500.0, 'total_all_due': 300.0}])

        with freeze_time('2016-01-01'):
            self.assertLinesValues(
                # pylint: disable=C0326
                report._get_lines(options),
                #   Name                                        Date,        Due Date,  Amount,       Balance
                [   0,                                      1,              2,       3,             5],
                [
                    ('partner_a',                                  '',             '',   300.0,          300.0),
                    ('INV/2016/00001',                   '01/01/2016',   '01/01/2016',   500.0,          500.0),
                    ('BILL/2016/01/0001',                '01/01/2016',   '01/01/2016',  -200.0,          300.0),
                    ('Total partner_a',                            '',             '',   300.0,          300.0),
                    ('Total',                                      '',             '',   300.0,          300.0),
                ],
                options,
            )

    def test_automatic_followup_report_attachments(self):
        followup_line = self.env['account_followup.followup.line'].create({
            'company_id': self.env.company.id,
            'name': 'First Reminder',
            'delay': 15,
            'send_email': True,
        })
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 500,
                'tax_ids': [],
            })]
        })
        invoice.action_post()

        self.assertPartnerFollowup(self.partner_a, 'in_need_of_action', followup_line)

        invoice_attachment = self.env['ir.attachment'].create({
            'name': 'some_attachment.pdf',
            'res_id': invoice.id,
            'res_model': 'account.move',
            'datas': 'test',
            'type': 'binary',
        })
        send_wizard = self.env['account.move.send.wizard']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({'sending_methods': ['manual']})
        send_wizard.action_send_and_print()

        self.partner_a._compute_unpaid_invoices()
        with patch.object(self.env.registry['account.report'], 'export_to_pdf', autospec=True, side_effect=lambda *args, **kwargs: {'file_name': 'fake_partner_ledger.pdf', 'file_content': b'', 'file_type': 'pdf'}):
            self.partner_a.action_manually_process_automatic_followups()

        sent_attachments = self.env['mail.message'].search([('partner_ids', '=', self.partner_a.id)]).attachment_ids
        self.assertEqual(sent_attachments.mapped('name'), [f'{self.partner_a.name} - fake_partner_ledger.pdf', invoice._get_invoice_report_filename()])

    def test_manual_followup_report_invoices_removed(self):
        followup_line = self.env['account_followup.followup.line'].create({
            'company_id': self.env.company.id,
            'name': 'First Reminder',
            'delay': 15,
            'send_email': True,
        })
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 500,
                'tax_ids': [],
            })]
        })
        invoice.action_post()

        self.assertPartnerFollowup(self.partner_a, 'in_need_of_action', followup_line)

        invoice_attachment = self.env['ir.attachment'].create({
            'name': 'some_attachment.pdf',
            'res_id': invoice.id,
            'res_model': 'account.move',
            'datas': 'test',
            'type': 'binary',
        })
        invoice._message_set_main_attachment_id(invoice_attachment)

        self.partner_a._compute_unpaid_invoices()
        with patch.object(self.env.registry['account.report'], 'export_to_pdf', autospec=True, side_effect=lambda *args, **kwargs: {'file_name': 'fake_partner_ledger.pdf', 'file_content': b'', 'file_type': 'pdf'}):
            self.partner_a._execute_followup_partner(options={
                'partner_id': self.partner_a.id,
                'manual_followup': True,
                'snailmail': False,
                'join_invoices': True,
                'attachment_ids': [],
            })

        sent_attachments = self.env['mail.message'].search([('partner_ids', '=', self.partner_a.id)]).attachment_ids
        self.assertEqual(sent_attachments.mapped('name'), [f'{self.partner_a.name} - fake_partner_ledger.pdf'])

    def test_manual_followup_report_no_join_invoices(self):
        followup_line = self.env['account_followup.followup.line'].create({
            'company_id': self.env.company.id,
            'name': 'First Reminder',
            'delay': 15,
            'send_email': True,
        })
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 500,
                'tax_ids': [],
            })]
        })
        invoice.action_post()

        self.assertPartnerFollowup(self.partner_a, 'in_need_of_action', followup_line)

        invoice_attachment, followup_attachment = self.env['ir.attachment'].create([{
            'name': 'some_attachment.pdf',
            'res_id': invoice.id,
            'res_model': 'account.move',
            'datas': 'test',
            'type': 'binary',
        }, {
            'name': 'other_attachment.pdf',
            'datas': b64encode(b'my_test'),
            'type': 'binary',
        }])
        invoice._message_set_main_attachment_id(invoice_attachment)

        self.partner_a._compute_unpaid_invoices()
        with patch.object(self.env.registry['account.report'], 'export_to_pdf', autospec=True, side_effect=lambda *args, **kwargs: {'file_name': 'fake_partner_ledger.pdf', 'file_content': b'', 'file_type': 'pdf'}):
            self.partner_a._execute_followup_partner(options={
                'partner_id': self.partner_a.id,
                'manual_followup': True,
                'snailmail': False,
                'join_invoices': False,
                'attachment_ids': invoice_attachment.ids + followup_attachment.ids,
            })

        sent_attachments = self.env['mail.message'].search([('partner_ids', '=', self.partner_a.id)]).attachment_ids
        self.assertEqual(sent_attachments.mapped('name'), [f'{self.partner_a.name} - fake_partner_ledger.pdf'])

    def test_manual_followup_report_join_invoices(self):
        followup_line = self.env['account_followup.followup.line'].create({
            'company_id': self.env.company.id,
            'name': 'First Reminder',
            'delay': 15,
            'send_email': True,
        })
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 500,
                'tax_ids': [],
            })]
        })
        invoice.action_post()

        self.assertPartnerFollowup(self.partner_a, 'in_need_of_action', followup_line)

        invoice_attachment, followup_attachment = self.env['ir.attachment'].create([{
            'name': 'some_attachment.pdf',
            'res_id': invoice.id,
            'res_model': 'account.move',
            'datas': 'test',
            'type': 'binary',
        }, {
            'name': 'other_attachment.pdf',
            'datas': b64encode(b'my_test'),
            'type': 'binary',
        }])
        invoice._message_set_main_attachment_id(invoice_attachment)

        with patch.object(self.env.registry['account.report'], 'export_to_pdf', autospec=True, side_effect=lambda *args, **kwargs: {'file_name': 'fake_partner_ledger.pdf', 'file_content': b'', 'file_type': 'pdf'}):
            self.partner_a._execute_followup_partner(options={
                'partner_id': self.partner_a.id,
                'manual_followup': True,
                'snailmail': False,
                'join_invoices': True,
                'attachment_ids': invoice_attachment.ids + followup_attachment.ids,
            })

        sent_attachments = self.env['mail.message'].search([('partner_ids', '=', self.partner_a.id)]).attachment_ids
        self.assertEqual(sent_attachments.mapped('name'), [f'{self.partner_a.name} - fake_partner_ledger.pdf', 'other_attachment.pdf', 'some_attachment.pdf'])

    def _prepare_invoices_and_attachments(self):
        invoice_1 = self.init_invoice("out_invoice", amounts=[1000], post=True)
        invoice_2 = self.init_invoice("out_invoice", amounts=[2000], post=True)

        attachment_1 = self.env['ir.attachment'].create({
            'name': 'att_1.pdf',
            'res_id': invoice_1.id,
            'res_model': 'account.move',
            'datas': 'test',
            'type': 'binary',
        })
        invoice_1._message_set_main_attachment_id(attachment_1)

        attachment_2 = self.env['ir.attachment'].create([{
            'name': 'att_2.pdf',
            'res_id': invoice_2.id,
            'res_model': 'account.move',
            'res_field': 'invoice_pdf_report_file',  # simulates send & print
            'datas': 'test',
            'type': 'binary',
        }])

        return invoice_1 + invoice_2, attachment_1 + attachment_2

    def test_manual_followup_invoice_attachments_pdf_report_file(self):
        invoices, attachments = self._prepare_invoices_and_attachments()
        wizard = self.env['account_followup.manual_reminder'].with_context(
            active_model='res.partner',
            active_ids=invoices[1].partner_id.ids,
        ).create({})

        self.assertEqual(invoices[1].partner_id.unreconciled_aml_ids.move_id, invoices)
        self.assertEqual(wizard.attachment_ids, attachments[1], "The manually uploaded PDF should not be attached to the follow-up.")

    def test_auto_followup_invoice_attachments_pdf_report_file(self):
        invoices, attachments = self._prepare_invoices_and_attachments()
        self.env['account_followup.followup.line'].create({
            'company_id': self.env.company.id,
            'name': 'First Reminder',
            'delay': 15,
            'send_email': True,
        })
        with patch.object(self.env.registry['account.report'], 'export_to_pdf', autospec=True, side_effect=lambda *args, **kwargs: {'file_name': 'fake_partner_ledger.pdf', 'file_content': b'', 'file_type': 'pdf'}):
            self.partner_a.action_manually_process_automatic_followups()

        sent_attachments = self.env['mail.message'].search([('partner_ids', '=', invoices.partner_id.id)]).attachment_ids
        self.assertEqual(sent_attachments.mapped('name'), [f'{self.partner_a.name} - fake_partner_ledger.pdf', attachments[1].name])

    def test_followup_report_with_entries(self):
        """
            Entries shouldn't have a due date or be added to total_overdue on the followup report and on the partner.
        """
        report = self.env['account.followup.report']
        options = {
            'partner_id': self.partner_a.id,
        }
        with freeze_time('2016-01-02'):
            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'invoice_date': '2016-01-01',
                'invoice_date_due': '2016-01-01',
                'invoice_payment_term_id': False,
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [Command.create({
                    'quantity': 1,
                    'price_unit': 300,
                    'tax_ids': [],
                })]
            })
            invoice.action_post()

            entry = self.env['account.move'].create({
                'move_type': 'entry',
                'date': fields.Date.from_string('2016-01-02'),
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [
                    Command.create({
                        'name': 'line1',
                        'account_id': self.company_data['default_account_receivable'].id,
                        'debit': 500.0,
                        'credit': 0.0,
                    }),
                    Command.create({
                        'name': 'counterpart line',
                        'account_id': self.company_data['default_account_revenue'].id,
                        'debit': 0.0,
                        'credit': 500.0,
                    })
                ]
            })
            entry.action_post()

        with freeze_time('2016-01-15'):
            self.assertLinesValues(
                # pylint: disable=C0326
                report._get_followup_report_lines(options),
                #   Name                                    Date,           Due Date,       Doc.      Total Due
                [   0,                                      1,              2,              3,        5],
                [
                    ('MISC/2016/01/0001',                   '01/02/2016',   '',             '',       '$\xa0500.00'),
                    ('INV/2016/00001',                      '01/01/2016',   '01/01/2016',   '',       '$\xa0300.00'),
                    ('',                                    '',             '',             '',       '$\xa0800.00'),
                    ('',                                    '',             '',             '',       '$\xa0300.00'),
                ],
                options,
            )
            self.assertEqual(self.partner_a.total_due, 800)
            self.assertEqual(self.partner_a.total_overdue, 300)

    def test_action_report_followup(self):
        def _run_wkhtmltopdf(*args, **kwargs):
            return file_open('base/tests/minimal.pdf', 'rb').read()

        followup_line = self.env['account_followup.followup.line'].create({
            'company_id': self.env.company.id,
            'name': 'First Reminder',
            'delay': 15,
            'send_email': True,
        })
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 500,
                'tax_ids': [],
            })]
        })
        invoice.action_post()

        self.assertPartnerFollowup(self.partner_a, 'in_need_of_action', followup_line)

        with patch.object(self.env.registry['ir.actions.report'], '_run_wkhtmltopdf', _run_wkhtmltopdf):
            followup_letter = self.env['ir.actions.report'].with_context(force_report_rendering=True)._render_qweb_pdf('account_followup.report_followup_print_all', self.partner_a.id)[0]
        self.assertTrue(followup_letter)

    def test_automatic_followup_report_attachments_from_template(self):
        mail_template = self.env['mail.template'].create({
            'name': 'reminder',
            'model_id': self.env['ir.model']._get_id('res.partner'),
            'email_cc': 'john.carmac@example.me',
        })
        template_attachment = self.env['ir.attachment'].create({
            'name': 'template_attachment.pdf',
            'res_id': mail_template.id,
            'res_model': 'mail.template',
            'datas': 'test',
            'type': 'binary',
        })
        mail_template.attachment_ids = [template_attachment.id]

        dynamic_report = self.env['ir.actions.report'].create({
            'name': 'Test Report Partner',
            'model': 'res.partner',
            'report_name': 'account_followup.report_followup_print_all',
            'print_report_name': "'followup_dynamic_report'",
        })
        mail_template.report_template_ids = [dynamic_report.id]

        followup_line = self.env['account_followup.followup.line'].create({
            'company_id': self.env.company.id,
            'name': 'First Reminder',
            'delay': 15,
            'send_email': True,
            'mail_template_id': mail_template.id,
        })
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1,
                'price_unit': 500,
                'tax_ids': [],
            })]
        })
        invoice.action_post()
        self.assertPartnerFollowup(self.partner_a, 'in_need_of_action', followup_line)

        invoice_attachment = self.env['ir.attachment'].create({
            'name': 'invoice_attachment.pdf',
            'res_id': invoice.id,
            'res_model': 'account.move',
            'res_field': 'invoice_pdf_report_file',  # simulates send & print
            'datas': 'test',
            'type': 'binary',
        })
        invoice._message_set_main_attachment_id(invoice_attachment)

        self.partner_a._compute_unpaid_invoices()
        with patch.object(self.env.registry['account.report'], 'export_to_pdf', autospec=True, side_effect=lambda *args, **kwargs: {'file_name': 'fake_partner_ledger.pdf', 'file_content': b'', 'file_type': 'pdf'}):
            self.partner_a.action_manually_process_automatic_followups()

        sent_attachments = self.env['mail.message'].search([('partner_ids', '=', self.partner_a.id)]).attachment_ids
        self.assertEqual(sent_attachments.mapped('name'), ['followup_dynamic_report.html', f'{self.partner_a.name} - fake_partner_ledger.pdf', 'invoice_attachment.pdf', 'template_attachment.pdf'])
