# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from datetime import date

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import Form, users, warmup
from odoo.tests import tagged
from odoo.tools import formataddr, mute_logger


@tagged('post_install_l10n', 'post_install', '-at_install')
class AccountMoveSendBase(AccountTestInvoicingCommon, MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ensure print params
        cls.user_accountman = cls.env.user  # main account setup shadows users, better save it
        cls.company_main = cls.company_data['company']
        cls.company_main.invoice_is_email = True
        cls.company_main.invoice_is_download = False
        cls.move_template = cls.env['mail.template'].create({
            'auto_delete': True,
            'body_html': '<p>TemplateBody for <t t-out="object.name"></t><t t-out="object.invoice_user_id.signature or \'\'"></t></p>',
            'description': 'Sent to customers with their invoices in attachment',
            'email_from': "{{ (object.invoice_user_id.email_formatted or user.email_formatted) }}",
            'mail_server_id': cls.mail_server_global.id,
            'model_id': cls.env['ir.model']._get_id('account.move'),
            'name': "Invoice: Test Sending",
            'partner_to': "{{ object.partner_id.id }}",
            'subject': "{{ object.company_id.name }} Invoice (Ref {{ object.name or 'n/a' }})",
            'report_template_ids': [(4, cls.env.ref('account.account_invoices').id)],
            'lang': "{{ object.partner_id.lang }}",
        })
        cls.attachments = cls.env['ir.attachment'].create(
            cls._generate_attachments_data(
                2, cls.move_template._name, cls.move_template.id
            )
        )
        cls.move_template.write({
            'attachment_ids': [(6, 0, cls.attachments.ids)]
        })

        # test users + fetch admin user for testing (recipient, ...)
        cls.user_account = cls.env['res.users'].with_context(cls._test_context).create({
            'company_id': cls.company_main.id,
            'company_ids': [
                (6, 0, (cls.company_data['company'] + cls.company_data_2['company']).ids)
            ],
            'country_id': cls.env.ref('base.be').id,
            'email': 'e.e@example.com',
            'groups_id': [
                (6, 0, [cls.env.ref('base.group_user').id,
                        cls.env.ref('account.group_account_invoice').id,
                        cls.env.ref('base.group_partner_manager').id
                       ])
            ],
            'login': 'user_account',
            'name': 'Ernest Employee Account',
            'notification_type': 'inbox',
            'signature': '--\nErnest',
        })
        cls.user_account_other = cls.env['res.users'].with_context(cls._test_context).create({
            'company_id': cls.company_admin.id,
            'company_ids': [(4, cls.company_admin.id)],
            'country_id': cls.env.ref('base.be').id,
            'email': 'e.e.other@example.com',
            'groups_id': [
                (6, 0, [cls.env.ref('base.group_user').id,
                        cls.env.ref('account.group_account_invoice').id,
                        cls.env.ref('base.group_partner_manager').id
                       ])
            ],
            'login': 'user_account_other',
            'name': 'Eglantine Employee AccountOther',
            'notification_type': 'inbox',
            'signature': '--\nEglantine',
        })

        # mass mode: 10 invoices with their customer
        country_id = cls.env.ref('base.be').id
        langs = ['en_US', 'es_ES']
        cls.env['res.lang']._activate_lang('es_ES')
        cls.test_customers = cls.env['res.partner'].create([
            {'country_id': country_id,
             'email': f'test_partner_{idx}@test.example.com',
             'mobile': f'047500{idx:2d}{idx:2d}',
             'lang': langs[idx % len(langs)],
             'name': f'Partner_{idx}',
            } for idx in range(0, 10)
        ])
        cls.test_account_moves = cls.env['account.move'].create([{
            'invoice_date': date(2022, 3, 2),
            'invoice_date_due': date(2022, 3, 10),
            'invoice_line_ids': [
                (0, 0, {'name': 'Line1',
                        'price_unit': 100.0
                       }
                ),
                (0, 0, {'name': 'Line2',
                        'price_unit': 200.0
                       }
                ),
            ],
            'invoice_user_id': cls.user_account_other.id,
            'move_type': 'out_invoice',
            'name': f'INVOICE_{idx:02d}',
            'partner_id': cls.test_customers[idx].id,
        } for idx in range(0, 10)])

        cls.test_account_moves.action_post()

        # test impact of multi language support
        cls._activate_multi_lang(
            test_record=cls.test_account_moves,
            test_template=cls.move_template,
        )

    def setUp(self):
        super().setUp()

        # setup mail gateway to simulate complete reply-to computation
        self._init_mail_gateway()

        # patch registry to simulate a ready environment
        self.patch(self.env.registry, 'ready', True)
        self.flush_tracking()


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountComposerPerformance(AccountMoveSendBase):
    """ Test performance of custom composer for moves. """

    def test_assert_initial_values(self):
        """ Test initial values to ease understanding of results and notifications """
        for move in self.test_account_moves:
            with self.subTest(move=move):
                self.assertEqual(
                    move.invoice_user_id,
                    self.user_account_other,
                )
                self.assertEqual(
                    move.message_partner_ids,
                    self.user_accountman.partner_id + move.partner_id,
                )

    @users('user_account')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_move_composer_multi(self):
        """ Test with multi mode """
        test_moves = self.test_account_moves.with_env(self.env)
        test_customers = self.test_customers.with_env(self.env)
        move_template = self.move_template.with_env(self.env)

        for test_move in test_moves:
            self.assertFalse(test_move.is_move_sent)

        default_ctx = test_moves.action_send_and_print()['context']
        default_ctx['default_mail_template_id'] = move_template.id
        composer_form = Form(
            self.env['account.move.send'].with_context(default_ctx)
        )
        composer_form.checkbox_ubl_cii_xml = False
        composer = composer_form.save()

        with self.mock_mail_gateway(mail_unlink_sent=False):
            composer.action_send_and_print(from_cron=True)

        # check results: emails (mailing mode when being in multi)
        self.assertEqual(len(self._mails), 20, 'Should send an email to each invoice followers (accountman + partner)')
        for move, customer in zip(test_moves, test_customers):
            with self.subTest(move=move, customer=customer):
                _exp_move_name = move.name
                _exp_report_name = f"{move.name}.pdf"
                if move.partner_id.lang == 'es_ES':
                    _exp_body_tip = f'SpanishBody for {move.name}'
                    _exp_subject = f'SpanishSubject for {move.name}'
                else:
                    _exp_body_tip = f'TemplateBody for {move.name}'
                    _exp_subject = f'{self.env.user.company_id.name} Invoice (Ref {move.name})'

                self.assertEqual(move.partner_id, customer)
                self.assertMailMail(
                    customer,
                    'sent',
                    author=self.user_account_other.partner_id,  # author: synchronized with email_from of template
                    content=_exp_body_tip,
                    email_values={
                        'attachments_info': [
                            {'name': 'AttFileName_00.txt', 'raw': b'AttContent_00', 'type': 'text/plain'},
                            {'name': 'AttFileName_01.txt', 'raw': b'AttContent_01', 'type': 'text/plain'},
                            {'name': _exp_report_name, 'type': 'application/pdf'},
                        ],
                        'body_content': _exp_body_tip,
                        'email_from': self.user_account_other.email_formatted,
                        'subject': _exp_subject,
                        'reply_to': formataddr((
                            f'{move.company_id.name} {_exp_move_name}',
                            f'{self.alias_catchall}@{self.alias_domain}'
                        )),
                    },
                    fields_values={
                        'auto_delete': True,
                        'email_from': self.user_account_other.email_formatted,
                        'is_notification': True,  # should keep logs by default
                        'mail_server_id': self.mail_server_global,
                        'subject': _exp_subject,
                        'reply_to': formataddr((
                            f'{move.company_id.name} {_exp_move_name}',
                            f'{self.alias_catchall}@{self.alias_domain}'
                        )),
                    },
                )

        # composer configuration
        self.assertEqual(composer.move_ids, test_moves)
        self.assertTrue(composer.checkbox_send_mail)
        self.assertFalse(composer.checkbox_download)
        self.assertEqual(composer.mail_template_id, move_template)

        # invoice update
        for test_move in test_moves:
            self.assertTrue(test_move.is_move_sent)

    @users('user_account')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_move_composer_single(self):
        """ Test single mode """
        test_move = self.test_account_moves[0].with_env(self.env)
        test_customer = self.test_customers[0].with_env(self.env)
        move_template = self.move_template.with_env(self.env)

        default_ctx = test_move.action_send_and_print()['context']
        default_ctx['default_mail_template_id'] = move_template.id
        composer_form = Form(
            self.env['account.move.send'].with_context(default_ctx)
        )
        composer_form.checkbox_ubl_cii_xml = False
        composer = composer_form.save()

        with self.mock_mail_gateway(mail_unlink_sent=False), \
             self.mock_mail_app():
            composer.action_send_and_print()
            self.env.cr.flush()  # force tracking message

        self.assertEqual(len(self._new_msgs), 2, 'Should produce 2 messages: one for posting template, one for tracking')
        print_msg, track_msg = self._new_msgs[0], self._new_msgs[1]
        self.assertNotified(
            print_msg,
            [{
                'is_read': True,
                'partner': test_customer,
                'type': 'email',
            }],
        )

        # print: template-based message
        self.assertEqual(len(print_msg.attachment_ids), 3) # + factur-x.xml in tests
        self.assertNotIn(self.attachments, print_msg.attachment_ids,
                         'Attachments should be duplicated, not just linked')
        self.assertEqual(print_msg.author_id, self.user_account_other.partner_id,
                         'Should take invoice_user_id partner')
        self.assertEqual(print_msg.email_from, self.user_account_other.email_formatted,
                         'Should take invoice_user_id email')
        self.assertEqual(print_msg.notified_partner_ids, test_customer + self.user_accountman.partner_id)
        self.assertEqual(print_msg.subject, f'{self.env.user.company_id.name} Invoice (Ref {test_move.name})')
        # tracking: is_move_sent
        self.assertEqual(track_msg.author_id, self.env.user.partner_id)
        self.assertEqual(track_msg.email_from, self.env.user.email_formatted)
        self.assertTrue('is_move_sent' in track_msg.tracking_value_ids.field.mapped('name'))
        # sent email
        self.assertMailMail(
            test_customer,
            'sent',
            author=self.user_account_other.partner_id,  # author: synchronized with email_from of template
            content=f'TemplateBody for {test_move.name}',
            email_values={
                'attachments_info': [
                    {'name': 'AttFileName_00.txt', 'raw': b'AttContent_00', 'type': 'text/plain'},
                    {'name': 'AttFileName_01.txt', 'raw': b'AttContent_01', 'type': 'text/plain'},
                    {'name': f'{test_move.name}.pdf', 'type': 'application/pdf'},
                ],
                'body_content': f'TemplateBody for {test_move.name}',
                'email_from': self.user_account_other.email_formatted,
                'subject': f'{self.env.user.company_id.name} Invoice (Ref {test_move.name})',
                'reply_to': formataddr((
                    f'{test_move.company_id.name} {test_move.display_name}',
                    f'{self.alias_catchall}@{self.alias_domain}'
                )),
            },
            fields_values={
                'auto_delete': True,
                'email_from': self.user_account_other.email_formatted,
                'is_notification': True,  # should keep logs by default
                'mail_server_id': self.mail_server_global,
                'subject': f'{self.env.user.company_id.name} Invoice (Ref {test_move.name})',
                'reply_to': formataddr((
                    f'{test_move.company_id.name} {test_move.display_name}',
                    f'{self.alias_catchall}@{self.alias_domain}'
                )),
            },
        )

        # composer configuration
        self.assertEqual(len(composer.mail_attachments_widget), 3)
        self.assertIn(f'TemplateBody for {test_move.name}', composer.mail_body)
        self.assertEqual(composer.move_ids, test_move)
        self.assertTrue(composer.checkbox_send_mail)
        self.assertFalse(composer.checkbox_download)
        self.assertEqual(composer.mail_subject, f'{self.env.user.company_id.name} Invoice (Ref {test_move.name})')
        self.assertEqual(composer.mail_template_id, move_template)

        # invoice update
        self.assertTrue(test_move.is_move_sent)

    @users('user_account')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_move_composer_single_lang(self):
        """ Test single with another language """
        test_move = self.test_account_moves[1].with_env(self.env)
        test_customer = self.test_customers[1].with_env(self.env)
        move_template = self.move_template.with_env(self.env)

        default_ctx = test_move.action_send_and_print()['context']
        default_ctx['default_mail_template_id'] = move_template.id
        composer_form = Form(
            self.env['account.move.send'].with_context(default_ctx)
        )
        composer_form.checkbox_ubl_cii_xml = False
        composer = composer_form.save()

        with self.mock_mail_gateway(mail_unlink_sent=False), \
             self.mock_mail_app():
            composer.action_send_and_print()
            self.env.cr.flush()  # force tracking message

        self.assertEqual(len(self._new_msgs), 2, 'Should produce 2 messages: one for posting template, one for tracking')
        print_msg, track_msg = self._new_msgs[0], self._new_msgs[1]
        self.assertNotified(
            print_msg,
            [{
                'is_read': True,
                'partner': test_customer,
                'type': 'email',
            }],
        )

        # print: template-based message
        self.assertEqual(len(print_msg.attachment_ids), 3) # + factur-x.xml in tests
        self.assertNotIn(self.attachments, print_msg.attachment_ids,
                         'Attachments should be duplicated, not just linked')
        self.assertEqual(print_msg.author_id, self.user_account_other.partner_id,
                         'Should take invoice_user_id partner')
        self.assertEqual(print_msg.email_from, self.user_account_other.email_formatted,
                         'Should take invoice_user_id email')
        self.assertEqual(print_msg.notified_partner_ids, test_customer + self.user_accountman.partner_id)
        self.assertEqual(print_msg.subject, f'SpanishSubject for {test_move.name}')
        # tracking: is_move_sent
        self.assertEqual(track_msg.author_id, self.env.user.partner_id)
        self.assertEqual(track_msg.email_from, self.env.user.email_formatted)
        self.assertTrue('is_move_sent' in track_msg.tracking_value_ids.field.mapped('name'))
        # sent email
        self.assertMailMail(
            test_customer,
            'sent',
            author=self.user_account_other.partner_id,  # author: synchronized with email_from of template
            content=f'SpanishBody for {test_move.name}',  # translated version
            email_values={
                'attachments_info': [
                    {'name': 'AttFileName_00.txt', 'raw': b'AttContent_00', 'type': 'text/plain'},
                    {'name': 'AttFileName_01.txt', 'raw': b'AttContent_01', 'type': 'text/plain'},
                    {'name': f'{test_move.name}.pdf', 'type': 'application/pdf'},
                ],
                'body_content': f'SpanishBody for {test_move.name}',  # translated version
                'email_from': self.user_account_other.email_formatted,
                'subject': f'SpanishSubject for {test_move.name}',  # translated version
                'reply_to': formataddr((
                    f'{test_move.company_id.name} {test_move.display_name}',
                    f'{self.alias_catchall}@{self.alias_domain}'
                )),
            },
            fields_values={
                'auto_delete': True,
                'email_from': self.user_account_other.email_formatted,
                'is_notification': True,  # should keep logs by default
                'mail_server_id': self.mail_server_global,
                'subject': f'SpanishSubject for {test_move.name}',  # translated version
                'reply_to': formataddr((
                    f'{test_move.company_id.name} {test_move.display_name}',
                    f'{self.alias_catchall}@{self.alias_domain}'
                )),
            },
        )

        # composer configuration
        self.assertEqual(len(composer.mail_attachments_widget), 3)
        self.assertIn(f'SpanishBody for {test_move.name}', composer.mail_body,
                      'Should be translated, based on template')
        self.assertEqual(composer.move_ids, test_move)
        self.assertTrue(composer.checkbox_send_mail)
        self.assertFalse(composer.checkbox_download)
        self.assertEqual(composer.mail_subject, f'SpanishSubject for {test_move.name}',
                         'Should be translated, based on template')
        self.assertEqual(composer.mail_template_id, move_template)

        # invoice update
        self.assertTrue(test_move.is_move_sent)
