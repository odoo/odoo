# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import threading

from contextlib import contextmanager
from unittest.mock import patch, Mock

from odoo.tests.common import new_test_user, TransactionCase, HttpCase
from odoo import Command, modules

DISABLED_MAIL_CONTEXT = {
    'tracking_disable': True,
    'mail_create_nolog': True,
    'mail_create_nosubscribe': True,
    'mail_notrack': True,
    'no_reset_password': True,
}


class BaseCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Mail logic won't be tested by default in other modules.
        # Mail API overrides should be tested with dedicated tests on purpose
        # Hack to use with_context and avoid manual context dict modification
        cls.env = cls.env['base'].with_context(**cls.default_env_context()).env

        independent_user = cls.setup_independent_user()
        if independent_user:
            cls.env = cls.env(user=independent_user)
            cls.user = cls.env.user

        independent_company = cls.setup_independent_company()
        if independent_company:
            # avoid using the context to assign companies
            cls.env.user.company_id = independent_company
            cls.env.user.company_ids = [Command.set(independent_company.ids)]
        else:
            cls.setup_main_company()

        # Make sure all class variables have the same env.
        # Do not specify any class variables before the env changes.
        cls.company = cls.env.company
        cls.currency = cls.env.company.currency_id

        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
        })

        cls.group_portal = cls.env.ref('base.group_portal')
        cls.group_user = cls.env.ref('base.group_user')
        cls.group_system = cls.env.ref('base.group_system')

    @classmethod
    def default_env_context(cls):
        """ To Override to reactivate the tracking """
        return {**DISABLED_MAIL_CONTEXT}

    @classmethod
    def setup_other_currency(cls, code, **kwargs):
        rates = kwargs.pop('rates', [])
        currency = cls.env['res.currency'].with_context(active_test=False).search([('name', '=', code)], limit=1)
        currency.rate_ids.unlink()
        currency.write({
            'active': True,
            'rate_ids': [Command.create(
                {
                    'name': rate_date,
                    'rate': rate,
                    'company_id': cls.env.company.id,
                }
            ) for rate_date, rate in rates],
            **kwargs,
        })
        return currency

    @classmethod
    def setup_independent_company(cls, **kwargs):
        return None

    @classmethod
    def setup_independent_user(cls):
        return None

    @classmethod
    def get_default_groups(cls):
        return cls.env['res.users']._default_groups()

    @classmethod
    def setup_main_company(cls, currency_code='USD'):
        cls._use_currency(cls.env.company, currency_code)

    @classmethod
    def _enable_currency(cls, currency_code):
        currency = cls.env['res.currency'].with_context(active_test=False).search(
            [('name', '=', currency_code.upper())]
        )
        currency.action_unarchive()
        return currency

    @classmethod
    def _use_currency(cls, company, currency_code):
        # Enforce constant currency
        currency = cls._enable_currency(currency_code)
        if company.currency_id != currency:
            cls.env.transaction.cache.set(cls.env.company, type(cls.env.company).currency_id, currency.id, dirty=True)
            # this is equivalent to cls.env.company.currency_id = currency but without triggering buisness code checks.
            # The value is added in cache, and the cache value is set as dirty so that that
            # the value will be written to the database on next flush.
            # this was needed because some journal entries may exist when running tests, especially l10n demo data.

    @classmethod
    def _create_partner(cls, **create_values):
        return cls.env['res.partner'].create({
            'name': "Test Partner",
            'company_id': False,
            **create_values,
        })

    @classmethod
    def _create_company(cls, **create_values):
        company = cls.env['res.company'].create({
            'name': "Test Company",
            **create_values,
        })
        cls.env.user.company_ids = [Command.link(company.id)]
        # cls.env.context['allowed_company_ids'].append(company.id)
        return company

    @classmethod
    def _create_new_internal_user(cls, **kwargs):
        return new_test_user(
            cls.env,
            **({'login': 'internal_user'} | kwargs),
        )

    @classmethod
    def _create_new_portal_user(cls, **kwargs):
        return new_test_user(
            cls.env,
            groups='base.group_portal',
            **({'login': 'portal_user'} | kwargs),
        )


class BaseUsersCommon(BaseCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_portal = cls._create_new_portal_user()
        cls.user_internal = cls._create_new_internal_user()


class TransactionCaseWithUserDemo(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.ref('base.partner_admin').write({'name': 'Mitchell Admin'})
        cls.user_demo = cls.env['res.users'].search([('login', '=', 'demo')])
        cls.partner_demo = cls.user_demo.partner_id

        if not cls.user_demo:
            cls.env['ir.config_parameter'].sudo().set_param('auth_password_policy.minlength', 4)
            cls.partner_demo = cls.env['res.partner'].create({
                'name': 'Marc Demo',
                'email': 'mark.brown23@example.com',
            })
            cls.user_demo = cls.env['res.users'].create({
                'login': 'demo',
                'password': 'demo',
                'partner_id': cls.partner_demo.id,
                'groups_id': [Command.set([cls.env.ref('base.group_user').id, cls.env.ref('base.group_partner_manager').id])],
            })


class HttpCaseWithUserDemo(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_admin = cls.env.ref('base.user_admin')
        cls.user_admin.write({'name': 'Mitchell Admin'})
        cls.partner_admin = cls.user_admin.partner_id
        cls.user_demo = cls.env['res.users'].search([('login', '=', 'demo')])
        cls.partner_demo = cls.user_demo.partner_id

        if not cls.user_demo:
            cls.env['ir.config_parameter'].sudo().set_param('auth_password_policy.minlength', 4)
            cls.partner_demo = cls.env['res.partner'].create({
                'name': 'Marc Demo',
                'email': 'mark.brown23@example.com',
            })
            cls.user_demo = cls.env['res.users'].create({
                'login': 'demo',
                'password': 'demo',
                'partner_id': cls.partner_demo.id,
                'groups_id': [Command.set([cls.env.ref('base.group_user').id, cls.env.ref('base.group_partner_manager').id])],
            })


class SavepointCaseWithUserDemo(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_demo = cls.env['res.users'].search([('login', '=', 'demo')])
        cls.partner_demo = cls.user_demo.partner_id

        if not cls.user_demo:
            cls.env['ir.config_parameter'].sudo().set_param('auth_password_policy.minlength', 4)
            cls.partner_demo = cls.env['res.partner'].create({
                'name': 'Marc Demo',
                'email': 'mark.brown23@example.com',
            })
            cls.user_demo = cls.env['res.users'].create({
                'login': 'demo',
                'password': 'demo',
                'partner_id': cls.partner_demo.id,
                'groups_id': [Command.set([cls.env.ref('base.group_user').id, cls.env.ref('base.group_partner_manager').id])],
            })

    @classmethod
    def _load_partners_set(cls):
        cls.partner_category = cls.env['res.partner.category'].create({
            'name': 'Sellers',
            'color': 2,
        })
        cls.partner_category_child_1 = cls.env['res.partner.category'].create({
            'name': 'Office Supplies',
            'parent_id': cls.partner_category.id,
        })
        cls.partner_category_child_2 = cls.env['res.partner.category'].create({
            'name': 'Desk Manufacturers',
            'parent_id': cls.partner_category.id,
        })

        # Load all the demo partners
        cls.partners = cls.env['res.partner'].create([
            {
                'name': 'Inner Works', # Wood Corner
                'state_id': cls.env.ref('base.state_us_1').id,
                'category_id': [Command.set([cls.partner_category_child_1.id, cls.partner_category_child_2.id,])],
                'child_ids': [Command.create({
                    'name': 'Sheila Ruiz', # 'Willie Burke',
                }), Command.create({
                    'name': 'Wyatt Howard', # 'Ron Gibson',
                }), Command.create({
                    'name': 'Austin Kennedy', # Tom Ruiz
                })],
            }, {
                'name': 'Pepper Street', # 'Deco Addict',
                'state_id': cls.env.ref('base.state_us_2').id,
                'child_ids': [Command.create({
                    'name': 'Liam King', # 'Douglas Fletcher',
                }), Command.create({
                    'name': 'Craig Richardson', # 'Floyd Steward',
                }), Command.create({
                    'name': 'Adam Cox', # 'Addison Olson',
                })],
            }, {
                'name': 'AnalytIQ', #'Gemini Furniture',
                'state_id': cls.env.ref('base.state_us_3').id,
                'child_ids': [Command.create({
                    'name': 'Pedro Boyd', # Edwin Hansen
                }), Command.create({
                    'name': 'Landon Roberts', # 'Jesse Brown',
                    'company_id': cls.env.ref('base.main_company').id,
                }), Command.create({
                    'name': 'Leona Shelton', # 'Soham Palmer',
                }), Command.create({
                    'name': 'Scott Kim', # 'Oscar Morgan',
                })],
            }, {
                'name': 'Urban Trends', # 'Ready Mat',
                'state_id': cls.env.ref('base.state_us_4').id,
                'category_id': [Command.set([cls.partner_category_child_1.id, cls.partner_category_child_2.id,])],
                'child_ids': [Command.create({
                    'name': 'Louella Jacobs', # 'Billy Fox',
                }), Command.create({
                    'name': 'Albert Alexander', # 'Kim Snyder',
                }), Command.create({
                    'name': 'Brad Castillo', # 'Edith Sanchez',
                }), Command.create({
                    'name': 'Sophie Montgomery', # 'Sandra Neal',
                }), Command.create({
                    'name': 'Chloe Bates', # 'Julie Richards',
                }), Command.create({
                    'name': 'Mason Crawford', # 'Travis Mendoza',
                }), Command.create({
                    'name': 'Elsie Kennedy', # 'Theodore Gardner',
                })],
            }, {
                'name': 'Ctrl-Alt-Fix', # 'The Jackson Group',
                'state_id': cls.env.ref('base.state_us_5').id,
                'child_ids': [Command.create({
                    'name': 'carole miller', # 'Toni Rhodes',
                }), Command.create({
                    'name': 'Cecil Holmes', # 'Gordon Owens',
                })],
            }, {
                'name': 'Ignitive Labs', # 'Azure Interior',
                'state_id': cls.env.ref('base.state_us_6').id,
                'child_ids': [Command.create({
                    'name': 'Jonathan Webb', # 'Brandon Freeman',
                }), Command.create({
                    'name': 'Clinton Clark', # 'Nicole Ford',
                }), Command.create({
                    'name': 'Howard Bryant', # 'Colleen Diaz',
                })],
            }, {
                'name': 'Amber & Forge', # 'Lumber Inc',
                'state_id': cls.env.ref('base.state_us_7').id,
                'child_ids': [Command.create({
                    'name': 'Mark Webb', # 'Lorraine Douglas',
                })],
            }, {
                'name': 'Rebecca Day', # 'Chester Reed',
                'parent_id': cls.env.ref('base.main_partner').id,
            }, {
                'name': 'Gabriella Jennings', # 'Dwayne Newman',
                'parent_id': cls.env.ref('base.main_partner').id,
            }
        ])


class TransactionCaseWithUserPortal(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_portal = cls.env['res.users'].sudo().search([('login', '=', 'portal')])
        cls.partner_portal = cls.user_portal.partner_id

        if not cls.user_portal:
            cls.env['ir.config_parameter'].sudo().set_param('auth_password_policy.minlength', 4)
            cls.partner_portal = cls.env['res.partner'].create({
                'name': 'Joel Willis',
                'email': 'joel.willis63@example.com',
            })
            cls.user_portal = cls.env['res.users'].with_context(no_reset_password=True).create({
                'login': 'portal',
                'password': 'portal',
                'partner_id': cls.partner_portal.id,
                'groups_id': [Command.set([cls.env.ref('base.group_portal').id])],
            })


class HttpCaseWithUserPortal(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_portal = cls.env['res.users'].sudo().search([('login', '=', 'portal')])
        cls.partner_portal = cls.user_portal.partner_id

        if not cls.user_portal:
            cls.env['ir.config_parameter'].sudo().set_param('auth_password_policy.minlength', 4)
            cls.partner_portal = cls.env['res.partner'].create({
                'name': 'Joel Willis',
                'email': 'joel.willis63@example.com',
            })
            cls.user_portal = cls.env['res.users'].with_context(no_reset_password=True).create({
                'login': 'portal',
                'password': 'portal',
                'partner_id': cls.partner_portal.id,
                'groups_id': [Command.set([cls.env.ref('base.group_portal').id])],
            })


class MockSmtplibCase:
    """Class which allows you to mock the smtplib feature, to be able to test in depth the
    sending of emails. Unlike "MockEmail" which mocks mainly the <ir.mail_server> methods,
    here we mainly mock the smtplib to be able to test the <ir.mail_server> model.
    """
    @contextmanager
    def mock_smtplib_connection(self):
        self.emails = []

        origin = self

        class TestingSMTPSession:
            """SMTP session object returned during the testing.

            So we do not connect to real SMTP server. Store the mail
            server id used for the SMTP connection and other information.

            Can be mocked for testing to know which with arguments the email was sent.
            """
            def quit(self):
                pass

            def send_message(self, message, smtp_from, smtp_to_list):
                origin.emails.append({
                    'smtp_from': smtp_from,
                    'smtp_to_list': smtp_to_list,
                    'message': message.as_string(),
                    'from_filter': self.from_filter,
                })

            def sendmail(self, smtp_from, smtp_to_list, message_str, mail_options):
                origin.emails.append({
                    'smtp_from': smtp_from,
                    'smtp_to_list': smtp_to_list,
                    'message': message_str,
                    'from_filter': self.from_filter,
                })

            def set_debuglevel(self, smtp_debug):
                pass

            def ehlo_or_helo_if_needed(self):
                pass

            def login(self, user, password):
                pass

            def starttls(self, keyfile=None, certfile=None, context=None):
                pass

        self.testing_smtp_session = TestingSMTPSession()

        IrMailServer = self.env['ir.mail_server']
        connect_origin = type(IrMailServer).connect
        find_mail_server_origin = type(IrMailServer)._find_mail_server

        # custom mock to avoid losing context
        def mock_function(func):
            mock = Mock()

            def _call(*args, **kwargs):
                mock(*args[1:], **kwargs)
                return func(*args, **kwargs)

            _call.mock = mock
            return _call

        with patch('smtplib.SMTP_SSL', side_effect=lambda *args, **kwargs: self.testing_smtp_session), \
             patch('smtplib.SMTP', side_effect=lambda *args, **kwargs: self.testing_smtp_session), \
             patch.object(modules.module, 'current_test', False), \
             patch.object(type(IrMailServer), 'connect', mock_function(connect_origin)) as connect_mocked, \
             patch.object(type(IrMailServer), '_find_mail_server', mock_function(find_mail_server_origin)) as find_mail_server_mocked:
            self.connect_mocked = connect_mocked.mock
            self.find_mail_server_mocked = find_mail_server_mocked.mock
            yield

    def _build_email(self, mail_from, return_path=None, **kwargs):
        return self.env['ir.mail_server'].build_email(
            mail_from,
            kwargs.pop('email_to', 'dest@example-é.com'),
            kwargs.pop('subject', 'subject'),
            kwargs.pop('body', 'body'),
            headers={'Return-Path': return_path} if return_path else None,
            **kwargs,
        )

    def _send_email(self, msg, smtp_session):
        with patch.object(modules.module, 'current_test', False):
            self.env['ir.mail_server'].send_email(msg, smtp_session=smtp_session)
        return smtp_session.messages.pop()

    def assertSMTPEmailsSent(self, smtp_from=None, smtp_to_list=None, message_from=None,
                             mail_server=None, from_filter=None,
                             emails_count=1):
        """Check that the given email has been sent. If one of the parameter is
        None it is just ignored and not used to retrieve the email.

        :param smtp_from: FROM used for the authentication to the mail server
        :param smtp_to_list: List of destination email address
        :param message_from: FROM used in the SMTP headers
        :arap mail_server: used to compare the 'from_filter' as an alternative
          to using the from_filter parameter
        :param from_filter: from_filter of the <ir.mail_server> used to send the
          email. False means 'match everything';'
        :param emails_count: the number of emails which should match the condition
        :return: True if at least one email has been found with those parameters
        """
        if from_filter is not None and mail_server:
            raise ValueError('Invalid usage: use either from_filter either mail_server')
        if from_filter is None and mail_server is not None:
            from_filter = mail_server.from_filter
        matching_emails = filter(
            lambda email:
                (smtp_from is None or smtp_from == email['smtp_from'])
                and (smtp_to_list is None or smtp_to_list == email['smtp_to_list'])
                and (message_from is None or 'From: %s' % message_from in email['message'])
                and (from_filter is None or from_filter == email['from_filter']),
            self.emails,
        )

        debug_info = ''
        matching_emails_count = len(list(matching_emails))
        if matching_emails_count != emails_count:
            emails_from = []
            for email in self.emails:
                from_found = next((
                    line.split('From:')[1].strip() for line in email['message'].splitlines()
                    if line.startswith('From:')), '')
                emails_from.append(from_found)
            debug_info = '\n'.join(
                f"SMTP-From: {email['smtp_from']}, SMTP-To: {email['smtp_to_list']}, Msg-From: {email_msg_from}, From_filter: {email['from_filter']})"
                for email, email_msg_from in zip(self.emails, emails_from)
            )
        self.assertEqual(
            matching_emails_count, emails_count,
            msg=f'Incorrect emails sent: {matching_emails_count} found, {emails_count} expected'
                f'\nConditions\nSMTP-From: {smtp_from}, SMTP-To: {smtp_to_list}, Msg-From: {message_from}, From_filter: {from_filter}'
                f'\nNot found in\n{debug_info}'
        )

    @classmethod
    def _init_mail_gateway(cls):
        cls.default_from_filter = False
        cls.env['ir.config_parameter'].sudo().set_param('mail.default.from_filter', cls.default_from_filter)

    @classmethod
    def _init_mail_servers(cls):
        cls.env['ir.mail_server'].search([]).unlink()

        ir_mail_server_values = {
            'smtp_host': 'smtp_host',
            'smtp_encryption': 'none',
        }
        cls.mail_servers = cls.env['ir.mail_server'].create([
            {
                'name': 'Domain based server',
                'from_filter': 'test.mycompany.com',
                'sequence': 0,
                ** ir_mail_server_values,
            }, {
                'name': 'User specific server',
                'from_filter': 'specific_user@test.mycompany.com',
                'sequence': 1,
                ** ir_mail_server_values,
            }, {
                'name': 'Server Notifications',
                'from_filter': 'notifications.test@test.mycompany.com',
                'sequence': 2,
                ** ir_mail_server_values,
            }, {
                'name': 'Server No From Filter',
                'from_filter': False,
                'sequence': 3,
                ** ir_mail_server_values,
            },
        ])
        (
            cls.mail_server_domain, cls.mail_server_user,
            cls.mail_server_notification, cls.mail_server_default
        ) = cls.mail_servers
