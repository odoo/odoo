# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from unittest.mock import patch

from odoo.tests.common import TransactionCase, HttpCase
from odoo import Command


class TransactionCaseWithUserDemo(TransactionCase):

    def setUp(self):
        super(TransactionCaseWithUserDemo, self).setUp()

        self.env.ref('base.partner_admin').write({'name': 'Mitchell Admin'})
        self.user_demo = self.env['res.users'].search([('login', '=', 'demo')])
        self.partner_demo = self.user_demo.partner_id

        if not self.user_demo:
            self.env['ir.config_parameter'].sudo().set_param('auth_password_policy.minlength', 4)
            # YTI TODO: This could be factorized between the different classes
            self.partner_demo = self.env['res.partner'].create({
                'name': 'Marc Demo',
                'email': 'mark.brown23@example.com',
            })
            self.user_demo = self.env['res.users'].create({
                'login': 'demo',
                'password': 'demo',
                'partner_id': self.partner_demo.id,
                'groups_id': [Command.set([self.env.ref('base.group_user').id, self.env.ref('base.group_partner_manager').id])],
            })


class HttpCaseWithUserDemo(HttpCase):

    def setUp(self):
        super(HttpCaseWithUserDemo, self).setUp()
        self.user_admin = self.env.ref('base.user_admin')
        self.user_admin.write({'name': 'Mitchell Admin'})
        self.partner_admin = self.user_admin.partner_id
        self.user_demo = self.env['res.users'].search([('login', '=', 'demo')])
        self.partner_demo = self.user_demo.partner_id

        if not self.user_demo:
            self.env['ir.config_parameter'].sudo().set_param('auth_password_policy.minlength', 4)
            self.partner_demo = self.env['res.partner'].create({
                'name': 'Marc Demo',
                'email': 'mark.brown23@example.com',
            })
            self.user_demo = self.env['res.users'].create({
                'login': 'demo',
                'password': 'demo',
                'partner_id': self.partner_demo.id,
                'groups_id': [Command.set([self.env.ref('base.group_user').id, self.env.ref('base.group_partner_manager').id])],
            })


class SavepointCaseWithUserDemo(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(SavepointCaseWithUserDemo, cls).setUpClass()

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

class HttpCaseWithUserPortal(HttpCase):

    def setUp(self):
        super(HttpCaseWithUserPortal, self).setUp()
        self.user_portal = self.env['res.users'].search([('login', '=', 'portal')])
        self.partner_portal = self.user_portal.partner_id

        if not self.user_portal:
            self.env['ir.config_parameter'].sudo().set_param('auth_password_policy.minlength', 4)
            self.partner_portal = self.env['res.partner'].create({
                'name': 'Joel Willis',
                'email': 'joel.willis63@example.com',
            })
            self.user_portal = self.env['res.users'].with_context(no_reset_password=True).create({
                'login': 'portal',
                'password': 'portal',
                'partner_id': self.partner_portal.id,
                'groups_id': [Command.set([self.env.ref('base.group_portal').id])],
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

        self.testing_smtp_session = TestingSMTPSession()

        IrMailServer = self.env['ir.mail_server']
        connect = IrMailServer.connect
        find_mail_server = IrMailServer._find_mail_server

        with patch.object(type(IrMailServer), '_is_test_mode', lambda self: False), \
             patch('smtplib.SMTP_SSL', side_effect=lambda *args, **kwargs: self.testing_smtp_session), \
             patch('smtplib.SMTP', side_effect=lambda *args, **kwargs: self.testing_smtp_session), \
             patch.object(type(IrMailServer), 'connect', side_effect=connect) as connect_mocked, \
             patch.object(type(IrMailServer), '_find_mail_server', side_effect=find_mail_server) as find_mail_server_mocked:
            self.connect_mocked = connect_mocked
            self.find_mail_server_mocked = find_mail_server_mocked
            yield

    def assert_email_sent_smtp(self, smtp_from=None, smtp_to_list=None, message_from=None, from_filter=None, emails_count=1):
        """Check that the given email has been sent.

        If one of the parameter is None, it's just ignored and not used to retrieve the email.

        :param smtp_from: FROM used for the authentication to the mail server
        :param smtp_to_list: List of destination email address
        :param message_from: FROM used in the SMTP headers
        :param from_filter: from_filter of the <ir.mail_server> used to send the email
            Can use a lambda to check the value
        :param emails_count: the number of emails which should match the condition
        :return: True if at least one email has been found with those parameters
        """
        matching_emails = filter(
            lambda email:
                (smtp_from is None or (
                    smtp_from(email['smtp_from'])
                    if callable(smtp_from)
                    else smtp_from == email['smtp_from'])
                 )
                and (smtp_to_list is None or smtp_to_list == email['smtp_to_list'])
                and (message_from is None or 'From: %s' % message_from in email['message'])
                and (from_filter is None or from_filter == email['from_filter']),
            self.emails,
        )

        matching_emails_count = len(list(matching_emails))

        self.assertTrue(
            matching_emails_count == emails_count,
            msg='Emails not sent, %i emails match the condition but %i are expected' % (matching_emails_count, emails_count),
        )

    @classmethod
    def _init_mail_servers(cls):
        cls.env['ir.config_parameter'].sudo().set_param('mail.catchall.domain', 'test.com')
        cls.env['ir.config_parameter'].sudo().set_param('mail.default.from', 'notifications')
        cls.env['ir.config_parameter'].sudo().set_param('mail.bounce.alias', 'bounce')

        cls.alias_bounce = 'bounce'
        cls.alias_domain = 'test.com'

        cls.env['ir.mail_server'].search([]).unlink()

        ir_mail_server_values = {
            'smtp_host': 'smtp_host',
            'smtp_encryption': 'none',
        }
        (
            cls.server_domain,
            cls.server_user,
            cls.server_notification,
            cls.server_default,
        ) = cls.env['ir.mail_server'].create([
            {
                'name': 'Domain based server',
                'from_filter': 'test.com',
                ** ir_mail_server_values,
            }, {
                'name': 'User specific server',
                'from_filter': 'specific_user@test.com',
                ** ir_mail_server_values,
            }, {
                'name': 'Server Notifications',
                'from_filter': 'notifications@test.com',
                ** ir_mail_server_values,
            }, {
                'name': 'Server No From Filter',
                'from_filter': False,
                ** ir_mail_server_values,
            },
        ])
