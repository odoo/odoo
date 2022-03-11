# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import Form, users, warmup
from odoo.tests import tagged
from odoo.tools import formataddr, mute_logger


@tagged('mail_performance', 'account_performance', 'post_install', '-at_install')
class BaseMailAccountPerformance(MailCommon):
    """ Base main class for performance tests related to mail usage in accounting.

    TDE note: explanation for query counters.
      * assertQueryCount has highest counters in order to have green builds. Those
        are generally matching enterprise builds counters (all modules including
        enterprise modules);
      * "acc" stands for developer-friendly accounting (install account with
        enterprise, run tests);
      * "com" stands for community runbot (all modules, community only);
      * "ent" stands for enterprise runbot (all modules, enterprise build).
        Sometimes enterprise may be lower than community due to some ORM side
        effect (happens rarely);
      * those 3 values may differ due to side effects in sub-addons. Fixing it
        is a long-term work. Having them displayed allows to ease maintenance and
        seeing if local changes (e.g. fixes in account or mail) have an effect
        on query counters without having to wait on complete runbot builds;
    """

    @classmethod
    def setUpClass(cls):
        super(BaseMailAccountPerformance, cls).setUpClass()

        # ensure print params
        cls.company_admin.invoice_is_email = True
        cls.company_admin.invoice_is_print = True
        cls.default_template = cls.env.ref('account.email_template_edi_invoice')

        # test impact of multi language support
        cls._activate_multi_lang(
            test_record=cls.env['account.move'],
            test_template=cls.default_template
        )

        # test users + fetch admin user for testing (recipient, ...)
        cls.user_account = cls.env['res.users'].with_context(cls._test_context).create({
            'company_id': cls.company_admin.id,
            'company_ids': [(4, cls.company_admin.id)],
            'country_id': cls.env.ref('base.be').id,
            'email': 'e.e@example.com',
            'groups_id': [
                (6, 0, [cls.env.ref('base.group_user').id,
                        cls.env.ref('account.group_account_invoice').id,
                        cls.env.ref('base.group_partner_manager').id
                       ])
            ],
            'login': 'user_account',
            'name': 'Ernest Employee',
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
            'name': 'Eglantine Employee',
            'notification_type': 'inbox',
            'signature': '--\nEglantine',
        })
        cls.user_portal = cls.env['res.users'].with_context(cls._test_context).create({
            'company_id': cls.company_admin.id,
            'company_ids': [(4, cls.company_admin.id)],
            'country_id': cls.env.ref('base.be').id,
            'email': 'p.p@example.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_portal').id])],
            'login': 'user_portal',
            'name': 'Olivia Portal',
            'notification_type': 'email',
            'signature': '--\nOlivia',
        })

        # mass mode: 10 invoices with their customer
        country_id = cls.env.ref('base.be').id
        langs = ['en_US', 'es_ES']
        cls.test_customers = cls.env['res.partner'].create([
            {'country_id': country_id,
             'email': 'test_partner_%s@test.example.com' % x,
             'mobile': '047500%02d%02d' % (x, x),
             'lang': langs[x % len(langs)],
             'name': 'Partner_%s' % x,
            } for x in range(0, 10)
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
            'name': 'INVOICE_%02d' % x,
            'partner_id': cls.test_customers[x].id,
        } for x in range(0, 10)])

        # mono mode
        cls.test_account_move = cls.test_account_moves[0]
        cls.test_customer = cls.test_customers[0]

    def setUp(self):
        super(BaseMailAccountPerformance, self).setUp()

        # setup mail gateway to simulate complete reply-to computation
        self._init_mail_gateway()

        # patch registry to simulate a ready environment
        self.patch(self.env.registry, 'ready', True)
        self.flush_tracking()


@tagged('mail_performance', 'account_performance', 'post_install', '-at_install')
class TestAccountComposerPerformance(BaseMailAccountPerformance):
    """ Test performance of custom composer for moves. """

    @users('user_account')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_move_composer_multi(self):
        with self.assertQueryCount(user_account=19):  # acc: 19 / com 19
            account_moves = self.env['account.move'].browse(self.test_account_moves.ids)
            default_ctx = account_moves.action_send_and_print()['context']
            composer = self.env['account.invoice.send'].with_context(default_ctx).create({})
            composer.onchange_is_email()

        with self.mock_mail_gateway(mail_unlink_sent=True), \
             self.assertQueryCount(user_account=508):  # acc: 507 / com 483
            composer.send_and_print_action()

        self.assertEqual(len(self._new_mails), 10)
        for index, move in enumerate(self.test_account_moves):
            if move.partner_id.lang == 'es_ES':
                _exp_subject = 'SpanishSubject for %s' % move.name
                _exp_body_tip = '<p>SpanishBody for %s</p>' % move.name
            else:
                _exp_subject = '%s Invoice (Ref %s)' % (self.env.user.company_id.name, move.name)
                _exp_body_tip = 'Please remit payment at your earliest convenience'

            self.assertEqual(move.partner_id, self.test_customers[index])
            self.assertSentEmail(self.user_account_other.email_formatted,
                                 move.partner_id,
                                 body_content=_exp_body_tip,
                                 subject=_exp_subject,
                                 reply_to=formataddr(
                                    ('%s %s' % (move.company_id.name, move.display_name),
                                     '%s@%s' % (self.alias_catchall, self.alias_domain))
                                 ),
                                )

    @users('user_account')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_move_composer_multi_form(self):
        with self.assertQueryCount(user_account=17):  # acc: 15 / com 15
            account_moves = self.env['account.move'].browse(self.test_account_moves.ids)
            default_ctx = account_moves.action_send_and_print()['context']
            composer_form = Form(self.env['account.invoice.send'].with_context(default_ctx))

        with self.mock_mail_gateway(mail_unlink_sent=True), \
             self.mock_mail_app(), \
             self.assertQueryCount(user_account=510):  # acc: 509 / com 489
            composer = composer_form.save()
            composer.send_and_print_action()

        self.assertEqual(len(self._new_mails), 10)
        for index, move in enumerate(self.test_account_moves):
            if move.partner_id.lang == 'es_ES':
                _exp_subject = 'SpanishSubject for %s' % move.name
                _exp_body_tip = '<p>SpanishBody for %s</p>' % move.name
            else:
                _exp_subject = '%s Invoice (Ref %s)' % (self.env.user.company_id.name, move.name)
                _exp_body_tip = 'Please remit payment at your earliest convenience'

            self.assertEqual(move.partner_id, self.test_customers[index])
            self.assertSentEmail(self.user_account_other.email_formatted,
                                 move.partner_id,
                                 body_content=_exp_body_tip,
                                 subject=_exp_subject,
                                 reply_to=formataddr(
                                    ('%s %s' % (move.company_id.name, move.display_name),
                                     '%s@%s' % (self.alias_catchall, self.alias_domain))
                                 ),
                                )

    @users('user_account')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_move_composer_single(self):

        with self.assertQueryCount(user_account=57):  # acc: 57
            account_move = self.env['account.move'].browse(self.test_account_move.ids)
            default_ctx = account_move.action_send_and_print()['context']
            composer = self.env['account.invoice.send'].with_context(default_ctx).create({})
            composer.onchange_is_email()

        with self.mock_mail_gateway(mail_unlink_sent=True), \
             self.mock_mail_app(), \
             self.assertQueryCount(user_account=91):  # acc: 75 / com 78
            composer.send_and_print_action()

        _exp_subject = '%s Invoice (Ref %s)' % (self.env.user.company_id.name, account_move.name)
        # check composer configuration
        for str_bit in [self.test_customer.name, 'Here is your', 'Please remit payment at your earliest convenience', self.user_account_other.signature]:
            self.assertIn(str_bit, composer.body)
        self.assertEqual(composer.invoice_ids, account_move)
        self.assertTrue(composer.is_email)
        self.assertTrue(composer.is_print)
        self.assertEqual(composer.subject, _exp_subject)
        self.assertEqual(composer.template_id, self.env.ref('account.email_template_edi_invoice'))

        # check results
        self.assertTrue(account_move.is_move_sent)
        self.assertEqual(len(self._new_msgs), 2, 'Should produce 2 messages: one for posting template, one for tracking')
        print_msg = self._new_msgs[0]
        track_msg = self._new_msgs[1]
        self.assertEqual(track_msg.author_id, self.env.user.partner_id)
        self.assertEqual(track_msg.email_from, self.env.user.email_formatted)
        self.assertEqual(track_msg.tracking_value_ids.field.name, 'is_move_sent')
        self.assertEqual(print_msg.author_id, self.env.user.partner_id)
        self.assertEqual(print_msg.email_from, self.user_account_other.email_formatted, 'Should take invoice_user_id')
        self.assertEqual(print_msg.notified_partner_ids, self.test_customer)
        self.assertEqual(print_msg.subject, _exp_subject)

    @users('user_account')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_move_composer_single_form(self):
        with self.assertQueryCount(user_account=53):  # acc: 52 / com 51
            account_move = self.env['account.move'].browse(self.test_account_move.ids)
            default_ctx = account_move.action_send_and_print()['context']
            composer_form = Form(self.env['account.invoice.send'].with_context(default_ctx))

        with self.mock_mail_gateway(mail_unlink_sent=True), \
             self.mock_mail_app(), \
             self.assertQueryCount(user_account=120):  # acc: 103 / com 107
            composer = composer_form.save()
            composer.send_and_print_action()

        _exp_subject = '%s Invoice (Ref %s)' % (self.env.user.company_id.name, account_move.name)
        # check composer configuration
        for str_bit in [self.test_customer.name, 'Here is your', 'Please remit payment at your earliest convenience', self.user_account_other.signature]:
            self.assertIn(str_bit, composer.body)
        self.assertEqual(composer.invoice_ids, account_move)
        self.assertTrue(composer.is_email)
        self.assertTrue(composer.is_print)
        self.assertEqual(composer.subject, _exp_subject)
        self.assertEqual(composer.template_id, self.env.ref('account.email_template_edi_invoice'))

        # check results
        self.assertTrue(account_move.is_move_sent)
        self.assertEqual(len(self._new_msgs), 2, 'Should produce 2 messages: one for posting template, one for tracking')
        print_msg = self._new_msgs[0]
        track_msg = self._new_msgs[1]
        self.assertEqual(track_msg.author_id, self.env.user.partner_id)
        self.assertEqual(track_msg.email_from, self.env.user.email_formatted)
        self.assertEqual(track_msg.tracking_value_ids.field.name, 'is_move_sent')
        self.assertEqual(print_msg.author_id, self.env.user.partner_id)
        self.assertEqual(print_msg.email_from, self.user_account_other.email_formatted, 'Should take invoice_user_id')
        self.assertEqual(print_msg.notified_partner_ids, self.test_customer)
        self.assertEqual(print_msg.subject, _exp_subject)


@tagged('mail_performance', 'account_performance', 'post_install', '-at_install')
class TestAccountMailPerformance(BaseMailAccountPerformance):
    """ Test mail related features on a complex model using most of its
    features. """

    @users('user_account')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_move_track_responsible_email(self):
        self.user_admin.notification_type = 'email'
        self.assertEqual(self.test_account_moves.user_id, self.user_account_other)

        with self.mock_mail_gateway(mail_unlink_sent=True), \
             self.assertQueryCount(user_account=407):  # acc: 352 / com 407
            account_moves = self.env['account.move'].browse(self.test_account_moves.ids)
            account_moves.write({
                'user_id': self.user_admin.id,
                })

        # created mail.mail
        self.assertEqual(len(self._new_mails), 10)
        self.assertFalse(self._new_mails.exists(), 'Mail.mail should have been unlinked')
        # sent emails (cannot use mail tools as all emails are somehow similar)
        for email in self._mails:
            self.assertEqual(email['email_to'], [self.user_admin.email_formatted])


    @users('user_account')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_move_track_responsible_inbox(self):
        self.user_admin.notification_type = 'inbox'
        self.assertEqual(self.test_account_moves.user_id, self.user_account_other)

        with self.mock_mail_gateway(mail_unlink_sent=True), \
             self.assertQueryCount(user_account=183):  # acc: 178 / com 183
            account_moves = self.env['account.move'].browse(self.test_account_moves.ids)
            account_moves.write({
                'user_id': self.user_admin.id,
            })
