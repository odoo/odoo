from markupsafe import Markup
from unittest.mock import patch
from unittest.mock import DEFAULT
import base64

from odoo import exceptions, tools
from odoo.addons.mail.tests.common import mail_new_test_user, MailCommon
from odoo.addons.test_mail.models.test_mail_models import MailTestSimple
from odoo.addons.test_mail.tests.common import TestRecipients
from odoo.addons.mail.tools.discuss import Store
from odoo.tests import Form, users, warmup, tagged
from odoo.tools import mute_logger


class ThreadRecipients(MailCommon, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_portal = cls._create_portal_user()
        cls.test_partner, cls.test_partner_archived = cls.env['res.partner'].create([
            {
                'email': '"Test External" <test.external@example.com>',
                'phone': '+32455001122',
                'name': 'Name External',
            }, {
                'active': False,
                'email': '"Test Archived" <test.archived@example.com>',
                'phone': '+32455221100',
                'name': 'Name Archived',
            },
        ])
        cls.user_employee_2 = mail_new_test_user(
            cls.env,
            email='eglantine@example.com',
            groups='base.group_user',
            login='employee2',
            name='Eglantine Employee',
            notification_type='email',
            signature='--\nEglantine',
        )
        cls.partner_employee_2 = cls.user_employee_2.partner_id
        cls.user_employee_archived = mail_new_test_user(
            cls.env,
            email='albert@example.com',
            groups='base.group_user',
            login='albert',
            name='Albert Alemployee',
            notification_type='email',
            signature='--\nAlbert',
        )
        cls.user_employee_archived.active = False
        cls.partner_employee_archived = cls.user_employee_archived.partner_id

        cls.test_aliases = cls.env['mail.alias'].create([
            {
                'alias_domain_id': cls.mail_alias_domain.id,
                'alias_model_id': cls.env['ir.model']._get_id('mail.test.ticket.mc'),
                'alias_name': 'test.alias.free',
            }, {
                'alias_domain_id': cls.mail_alias_domain.id,
                'alias_model_id': cls.env['ir.model']._get_id('mail.test.ticket.mc'),
                'alias_name': 'test.alias.partner',
            }, {
                'alias_domain_id': cls.mail_alias_domain.id,
                'alias_incoming_local': True,
                'alias_model_id': cls.env['ir.model']._get_id('mail.test.ticket.mc'),
                'alias_name': 'test.alias.free.local',
            }
        ])
        cls.test_partner_alias = cls.env['res.partner'].create({
            'email': f'"Do not do this" <{cls.test_aliases[1].alias_full_name}>',
            'name': 'Someone created a partner with email=alias',
        })
        cls.test_partner_catchall = cls.env['res.partner'].create({
            'email': f'"Do not do this neither" <{cls.mail_alias_domain.catchall_email}>',
            'name': 'Someone created a partner with email=catchall',
        })


@tagged('mail_thread', 'mail_thread_api', 'mail_tools')
class TestAPI(ThreadRecipients):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.ticket_record = cls.env['mail.test.ticket.mc'].create({
            'company_id': cls.user_employee.company_id.id,
            'email_from': '"Paulette Vachette" <paulette@test.example.com>',
            'phone_number': '+32455998877',
            'name': 'Test',
            'user_id': cls.user_employee.id,
        })
        cls.ticket_records = cls.ticket_record + cls.env['mail.test.ticket.mc'].create([
            {
                'email_from': '"Maybe Paulette" <PAULETTE@test.example.com>',
                'name': 'Duplicate email',
            }, {
                'email_from': '"Multi Customer" <multi@test.example.com>, "Multi 2" <multi.2@test.example.com>',
                'name': 'Multi Email',
            }, {
                'email_from': 'wrong',
                'phone_number': '+32455000001',
                'name': 'Wrong email',
            }, {
                'email_from': 'wrong',
                'name': 'Duplicate Wrong email',
            }, {
                'email_from': False,
                'name': 'Falsy email',
            }, {
                'email_from': f'"Other Name" <{cls.test_partner.email_normalized}>',
                'name': 'Test Partner Email',
            }, {
                'customer_id': cls.user_public.partner_id.id,
                'name': 'Publicly Created',
            },
        ])

    def test_assert_initial_values(self):
        """ Just be sure of what we test """
        self.assertFalse(self.user_employee_archived.active)
        self.assertTrue(self.partner_employee_archived.active)

    @users('employee')
    def test_body_escape(self):
        """ Test various use cases involving HTML encoding / escaping """
        ticket_record = self.ticket_record.with_env(self.env)
        attachments = self.env['ir.attachment'].create(
            self._generate_attachments_data(2, 'mail.compose.message', 0)
        )
        self.assertFalse(self.env['ir.attachment'].sudo().search([('name', '=', 'test_image.jpeg')]))

        # attachments processing through CID, rewrites body (if escaped)
        body = '<div class="ltr"><img src="cid:ii_lps7a8sm0" alt="test_image.jpeg" width="542" height="253">Zboing</div>'
        for with_markup in [False, True]:
            with self.subTest(with_markup=with_markup):
                test_body = Markup(body) if with_markup else body
                message = ticket_record.message_post(
                    attachments=[("test_image.jpeg", "b", {"cid": "ii_lps7a8sm0"})],
                    attachment_ids=attachments.ids,
                    body=test_body,
                    message_type="comment",
                    partner_ids=self.partner_1.ids,
                )
                new_attachment = self.env['ir.attachment'].sudo().search([('name', '=', 'test_image.jpeg')])
                self.assertEqual(new_attachment.res_id, ticket_record.id)
                if with_markup:
                    expected_body = Markup(
                        f'<div class="ltr"><img src="/web/image/{new_attachment.id}?access_token={new_attachment.access_token}" '
                         'alt="test_image.jpeg" width="542" height="253">Zboing</div>'
                    )
                else:
                    expected_body = Markup('<p>&lt;div class="ltr"&gt;&lt;img src="cid:ii_lps7a8sm0" alt="test_image.jpeg" width="542" height="253"&gt;Zboing&lt;/div&gt;</p>')
                self.assertEqual(message.attachment_ids, attachments + new_attachment)
                self.assertEqual(message.body, expected_body)
                new_attachment.unlink()

        # internals of attachment processing, in case it is called for other addons
        for with_markup in [False, True]:
            with self.subTest(with_markup=with_markup):
                message_values = {
                    'body': Markup(body) if with_markup else body,
                    'model': ticket_record._name,
                    'res_id': ticket_record.id,
                }
                processed_values = self.env['mail.thread']._process_attachments_for_post(
                    [("test_image.jpeg", "b", {"cid": "ii_lps7a8sm0"})], attachments.ids, message_values,
                )
                if not with_markup:
                    self.assertFalse('body' in processed_values, 'Mail: escaped html does not contain tags to handle anymore')
                else:
                    self.assertTrue(isinstance(processed_values['body'], Markup))

        # html is escaped in main API methods
        content = 'I am "Robert <robert@poilvache.com>"'
        expected = Markup('<p>I am "Robert &lt;robert@poilvache.com&gt;"</p>')  # enclosed in p to make valid html
        message = ticket_record._message_log(
            body=content,
        )
        self.assertEqual(message.body, expected)
        message = ticket_record.message_notify(
            body=content,
            partner_ids=self.partner_1.ids,
        )
        self.assertEqual(message.body, expected)
        message = ticket_record.message_post(
            body=content,
            message_type="comment",
            partner_ids=self.partner_1.ids,
        )
        self.assertEqual(message.body, expected)
        ticket_record._message_update_content(message, body="Hello <R&D/>")
        self.assertEqual(message.body, Markup('<p>Hello &lt;R&amp;D/&gt;<span class="o-mail-Message-edited"></span></p>'))

    @users('employee')
    def test_mail_partner_find_from_emails(self):
        """ Test '_partner_find_from_emails'. Multi mode is mainly targeting
        finding or creating partners based on record information or message
        history. """
        existing_partners = self.env['res.partner'].sudo().search([])
        tickets = self.ticket_records.with_user(self.env.user)
        self.assertEqual(len(tickets), 8)
        res = tickets._partner_find_from_emails({ticket: [ticket.email_from] for ticket in tickets}, no_create=False)
        self.assertEqual(len(tickets), len(res))

        # fetch partners that should have been created
        new = self.env['res.partner'].search([('email_normalized', '=', 'paulette@test.example.com')])
        self.assertEqual(len(new), 1, 'Should have created once the customer, even if found in various duplicates')
        self.assertNotIn(new, existing_partners)
        new_wrong = self.env['res.partner'].search([('email', '=', 'wrong')])
        self.assertEqual(len(new_wrong), 1, 'Should have created once the wrong email')
        self.assertNotIn(new, new_wrong)
        new_multi = self.env['res.partner'].search([('email_normalized', '=', 'multi@test.example.com')])
        self.assertEqual(len(new_multi), 1, 'Should have created a based for multi email, using the first found email')
        self.assertNotIn(new, new_multi)

        # assert results: found / create partners and their values (if applies)
        record_customer_values = {
            'company_id': self.user_employee.company_id,
            'email': 'paulette@test.example.com',
            'name': 'Paulette Vachette',
            'phone': '+32455998877',
        }
        expected_all = [
            (new, [record_customer_values]),
            (new, [record_customer_values]),
            (new_multi, [{  # not the actual record customer hence no mobile / phone, see _get_customer_information
                'company_id': self.user_employee.company_id,
                'email': 'multi@test.example.com',
                'name': 'Multi Customer',
                'phone': False,
            }]),
            (new_wrong, [{  # invalid email but can be fixed afterwards -> matches a potential customer
                'company_id': self.user_employee.company_id,
                'email': 'wrong',
                'name': 'wrong',
                'phone': '+32455000001',
            }]),
            (new_wrong, [{  # invalid email but can be fixed afterwards -> matches a potential customer
                'company_id': self.user_employee.company_id,
                'email': 'wrong',
                'name': 'wrong',
                'phone': '+32455000001',
            }]),
            (self.env['res.partner'], []),
            (self.test_partner, [{}]),
            (self.env['res.partner'], []),
        ]
        for ticket, (exp_partners, exp_values_list) in zip(tickets, expected_all):
            partners = res[ticket.id]
            with self.subTest(ticket_name=ticket.name):
                self.assertEqual(partners, exp_partners, f'Found {partners.name} instead of {exp_partners.name}')
                for partner, exp_values in zip(partners, exp_values_list, strict=True):
                    for fname, fvalue in exp_values.items():
                        self.assertEqual(partners[fname], fvalue)

    @users('employee')
    def test_mail_partner_find_from_emails_ordering(self):
        """ Test '_partner_find_from_emails' on a single record, to test notably
        ordering and filtering. """
        self.user_employee.write({'company_ids': [(4, self.company_2.id)]})
        # create a mess, mix of portal / internal users + customer, to test ordering
        portal_user, internal_user = self.env['res.users'].sudo().create([
            {
                'company_id': self.env.user.company_id.id,
                'email': 'test.ordering@test.example.com',
                'group_ids': [(4, self.env.ref('base.group_portal').id)],
                'login': 'order_portal',
                'name': 'Portal Test User for ordering',
            }, {
                'company_id': self.env.user.company_id.id,
                'email': 'test.ordering@test.example.com',
                'group_ids': [(4, self.env.ref('base.group_user').id)],
                'login': 'order_internal',
                'name': 'Zuper Internal Test User for ordering',  # name based: after portal
            }
        ])
        dupe_partners = self.env['res.partner'].create([
            {
                'company_id': self.company_2.id,
                'email': 'test.ordering@test.example.com',
                'name': 'Dupe Partner (C2)',
            }, {
                'company_id': False,
                'email': 'test.ordering@test.example.com',
                'name': 'Dupe Partner (NoC)',
            }, {
                'company_id': self.env.user.company_id.id,
                'email': 'test.ordering@test.example.com',
                'name': 'Dupe Partner (C1)',
            }, {
                'company_id': False,
                'email': '"ID ordering check" <test.ordering@test.example.com>',
                'name': 'A Dupe Partner (NoC)',  # name based: before other, but newest, check ID order
            },
        ])
        all_partners = portal_user.partner_id + internal_user.partner_id + dupe_partners
        self.assertTrue(portal_user.partner_id.id < internal_user.partner_id.id)
        self.assertTrue(internal_user.partner_id.id < dupe_partners[0].id)

        for active_partners, followers, expected in [
            # nothing to find
            (self.env['res.partner'], self.env['res.partner'], self.env['res.partner']),
            # one result, easy yay
            (dupe_partners[3], self.env['res.partner'], dupe_partners[3]),
            # various partners: should be id ASC, not name-based
            (dupe_partners[1] + dupe_partners[3], self.env['res.partner'], dupe_partners[1]),
            # involving matching company check: matching company wins
            (dupe_partners, self.env['res.partner'], dupe_partners[2]),
            # users > partner
            (portal_user.partner_id + dupe_partners, self.env['res.partner'], portal_user.partner_id),
            # internal user > any other user
            (portal_user.partner_id + internal_user.partner_id + dupe_partners, self.env['res.partner'], internal_user.partner_id),
            # follower > any other thing
            (internal_user.partner_id + dupe_partners, dupe_partners[0], dupe_partners[0]),
        ]:
            with self.subTest(names=active_partners.mapped('name'), followers=followers.mapped('name')):
                # removes (through deactivating) some partners to check ordering
                (portal_user + internal_user).filtered(lambda u: u.partner_id not in active_partners).active = False
                (all_partners - active_partners).active = False
                self.ticket_record.message_subscribe(followers.ids)

                ticket = self.ticket_record.with_user(self.env.user)
                partners = ticket._partner_find_from_emails(
                    {ticket: [ticket.email_from, 'test.ordering@test.example.com']},
                    no_create=True,
                )[ticket.id]

                # should find just one partner, the other one is not linked to any partner
                self.assertEqual(partners, expected, f'Found {partners.name} instead of {expected.name}')

                all_partners.active = True
                (portal_user + internal_user).active = True
                self.ticket_record.message_unsubscribe(followers.ids)

    @users('employee')
    def test_mail_partner_find_from_emails_record(self):
        """ On a given record, give several emails and check it is effectively
        based on record information. """
        ticket = self.ticket_record.with_user(self.env.user)
        partners = ticket._partner_find_from_emails(
            {ticket: [
                'raoul@test.example.com',
                ticket.email_from,
                self.test_partner.email,
            ]},
            no_create=False,
        )[ticket.id]

        # new - extra email
        other = partners[0]
        self.assertEqual(other.company_id, self.user_employee.company_id)
        self.assertEqual(other.email, "raoul@test.example.com")
        self.assertEqual(other.name, "raoul@test.example.com")
        # new - linked to record
        customer = partners[1]
        self.assertEqual(customer.company_id, self.user_employee.company_id)
        self.assertEqual(customer.email, "paulette@test.example.com")
        self.assertEqual(customer.phone, "+32455998877", "Should come from record, see '_get_customer_information'")
        self.assertEqual(customer.name, "Paulette Vachette")
        # found
        self.assertEqual(partners[2], self.test_partner)

    @users('employee')
    def test_mail_partner_find_from_emails_tweaks(self):
        """ Misc tweaks of '_partner_find_from_emails' """
        ticket = self.ticket_record.with_user(self.env.user)
        partner = ticket._partner_find_from_emails_single(
            [ticket.email_from],
            additional_values={'paulette@test.example.com': {'name': 'Forced Name', 'company_id': False}},
            no_create=False)
        self.assertFalse(partner.company_id, 'Forced by additional values')
        self.assertEqual(partner.email, 'paulette@test.example.com')
        self.assertEqual(partner.name, 'Forced Name', 'Forced by additional values')
        self.assertEqual(partner.phone, '+32455998877')

    @users('employee')
    @warmup
    def test_message_get_default_recipients(self):
        void_partner = self.env['res.partner'].sudo().create({'name': 'No Email'})
        test_records = self.env['mail.test.recipients'].create([
            {
                'customer_id': self.partner_1.id,
                'contact_ids': [(4, self.partner_2.id), (4, self.partner_1.id)],
                'name': 'Lots of partners',
            }, {
                'customer_id': self.partner_1.id,
                'customer_email': '"Forced" <forced@test.example.com>',
                'email_cc': '"CC" <email.cc@test.example.com>',
                'name': 'Email Forced + CC',
            }, {
                'customer_id': self.partner_1.id,
                'customer_email': False,
                'name': 'No email but partner',
            }, {
                'customer_email': '"Unknown" <unknown@test.example.com>',
                'name': 'Email only',
            }, {
                'email_cc': '"CC" <email.cc@test.example.com>',
                'name': 'CC only',
            }, {
                'customer_id': void_partner.id,
                'name': 'No info (void partner)',
            }, {
                'name': 'No info at all',
            }, {
                'customer_id': self.user_public.partner_id.id,
            }
        ])
        self.assertFalse(test_records[2].customer_email)
        self.flush_tracking()

        # test default computation of recipients
        self.env.invalidate_all()
        with self.assertQueryCount(14):
            defaults_withcc = test_records.with_context()._message_get_default_recipients(with_cc=True)
            defaults_withoutcc = test_records.with_context()._message_get_default_recipients()
        for record, expected in zip(test_records, [
            {
                # customer_id first for partner_ids; partner > email
                'email_cc': '', 'email_to': '',
                'partner_ids': (self.partner_1 + self.partner_2).ids,
            }, {
                # partner > email
                'email_cc': '"CC" <email.cc@test.example.com>', 'email_to': '', 'partner_ids': self.partner_1.ids,
            }, {
                # partner > email
                'email_cc': '', 'email_to': '', 'partner_ids': self.partner_1.ids,
            }, {
                'email_cc': '', 'email_to': '"Unknown" <unknown@test.example.com>', 'partner_ids': [],
            }, {
                'email_cc': '"CC" <email.cc@test.example.com>', 'email_to': '', 'partner_ids': [],
            }, {
                'email_cc': '', 'email_to': '', 'partner_ids': void_partner.ids,
            }, {
                'email_cc': '', 'email_to': '', 'partner_ids': [],
            }, {  # public user should not be proposed
                'email_cc': '', 'email_to': '', 'partner_ids': [],
            },
        ], strict=True):
            with self.subTest(name=record.name):
                self.assertEqual(defaults_withcc[record.id], expected)
                self.assertEqual(defaults_withoutcc[record.id], dict(expected, email_cc=''))

        # test default computation of recipients with email prioritized
        with patch.object(type(self.env["mail.test.recipients"]), "_mail_defaults_to_email", True):
            self.assertEqual(
                test_records[1]._message_get_default_recipients()[test_records[1].id],
                {'email_cc': '', 'email_to': '"Forced" <forced@test.example.com>', 'partner_ids': []},
                'Mail: prioritize email should not return partner if email is found'
            )
            self.assertEqual(
                test_records[2]._message_get_default_recipients()[test_records[2].id],
                {'email_cc': '', 'email_to': '', 'partner_ids': self.partner_1.ids},
                'Mail: prioritize email should not return partner if email is found'
            )

    @users('employee')
    def test_message_get_default_recipients_banned(self):
        """ Test defensive behavior to avoid contacting critical emails like
        aliases, public users, ... """
        tickets = self.env['mail.test.ticket.mc'].create([
            # do not propose public partners
            {
                'customer_id': self.user_public.partner_id.id,
                'name': 'Public',
            },
            # do not propose root
            {
                'customer_id': self.user_root.partner_id.id,
                'name': 'Root',
            },
            # do not propose alias domain emails
            {
                'email_from': self.mail_alias_domain.catchall_email,
                'name': 'Alias domain email',
            },
            # do not propose when partner = alias
            {
                'customer_id': self.test_partner_alias.id,
                'name': 'Partner = Alias',
            },
            # do not propose alias email
            {
                'email_from': self.test_aliases[0].alias_full_name,
                'name': 'Alias email',
            },
            # do not propose alias email (left-part pre-17 support)
            {
                'email_from': f'{self.test_aliases[2].alias_name}@other.domain',
                'name': 'Alias email (left-part compat)',
            },
            # do not propose alias email (even if linked to a partner)
            {
                'email_from': self.test_aliases[1].alias_full_name,
                'name': 'Alias email, existing partner',
            },
            # propose archived
            {
                'customer_id': self.test_partner_archived.id,
                'name': 'Archived partner',
            },
            # propose active based on archived user
            {
                'customer_id': self.partner_employee_archived.id,
                'name': 'Archived partner',
            },
        ])
        expected_all = [
            # nobody to suggest (no public !)
            {'email_cc': '', 'email_to': '', 'partner_ids': []},
            # should be nobody to suggest (no root !)
            {'email_cc': '', 'email_to': '', 'partner_ids': []},
            # alias domain email is not ok
            {'email_cc': '', 'email_to': '', 'partner_ids': []},
            # partner with alias email is not ok
            {'email_cc': '', 'email_to': '', 'partner_ids': []},
            # alias email is not ok
            {'email_cc': '', 'email_to': '', 'partner_ids': []},
            # left-part compat alias email is not ok
            {'email_cc': '', 'email_to': '', 'partner_ids': []},
            # alias email is not ok even if linked to partner
            {'email_cc': '', 'email_to': '', 'partner_ids': []},
            # archived is ok, customer
            {'email_cc': '', 'email_to': '', 'partner_ids': [self.test_partner_archived.id]},
            # active based on archived user is ok, customer
            {'email_cc': '', 'email_to': '', 'partner_ids': [self.partner_employee_archived.id]},
        ]
        defaults = tickets._message_get_default_recipients()
        for ticket, expected in zip(tickets, expected_all, strict=True):
            with self.subTest(ticket_name=ticket.name):
                self.assertDictEqual(defaults[ticket.id], expected)

    @users("employee")
    def test_message_get_suggested_recipients(self):
        """ Test default creation values returned for suggested recipient. """
        ticket = self.ticket_record.with_user(self.env.user)
        ticket.message_unsubscribe(ticket.user_id.partner_id.ids)
        suggestions = ticket._message_get_suggested_recipients(no_create=True)
        self.assertEqual(len(suggestions), 2)
        for suggestion, expected in zip(suggestions, [{
            'create_values': {},
            'email': self.user_employee.email_normalized,
            'name': self.user_employee.name,
            'partner_id': self.partner_employee.id,
        }, {
            'create_values': {
                'company_id': self.env.user.company_id.id,
                'phone': '+32455998877',
            },
            'email': 'paulette@test.example.com',
            'name': 'Paulette Vachette',
            'partner_id': False,
        }], strict=True):
            self.assertDictEqual(suggestion, expected)

        # existing partner not linked -> should propose it
        ticket_partner_email = self.env['mail.test.ticket.mc'].create({
            'customer_id': False,
            'email_from': self.test_partner.email_formatted,
            'name': 'Partner email',
            'phone_number': '+33199001015',
            'user_id': self.env.user.id,  # should not be proposed, already follower
        })
        # existing partner -> should propose it
        ticket_partner = self.env['mail.test.ticket.mc'].create({
            'customer_id': self.test_partner.id,
            'email_from': self.test_partner.email_formatted,
            'name': 'Partner',
        })
        # existing partner in followers -> should not propose it
        ticket_partner_fol = self.env['mail.test.ticket.mc'].create({
            'customer_id': self.test_partner.id,
            'email_from': self.test_partner.email_formatted,
            'name': 'Partner follower',
        })
        # existing partner in followers -> should not propose it
        ticket_partner_fol_user = self.env['mail.test.ticket.mc'].create({
            'customer_id': self.partner_employee.id,
            'email_from': self.partner_employee.email_formatted,
            'name': 'Partner follower (user)',
        })
        # existing partner with multiple emails -> should propose only the first one
        partner_multiemail = self.test_partner.copy({'email': 'test1.external@example.com,test2.external@example.com'})
        ticket_partner_multiemail = self.env['mail.test.ticket.mc'].create({
            'customer_id': partner_multiemail.id,
            'email_from': partner_multiemail.email_formatted,
            'name': 'Partner Multi-Emails',
        })
        ticket_partner_fol.message_subscribe(partner_ids=self.test_partner.ids)
        ticket_partner_fol.message_subscribe(partner_ids=self.partner_employee.ids)
        for ticket, sugg_partner in zip(
            ticket_partner_email + ticket_partner + ticket_partner_fol + ticket_partner_fol_user + ticket_partner_multiemail,
            (self.test_partner, self.test_partner, self.test_partner, False, partner_multiemail),
            strict=True,
        ):
            with self.subTest(ticket=ticket.name):
                suggestions = ticket._message_get_suggested_recipients(no_create=True)
                if sugg_partner:
                    self.assertEqual(len(suggestions), 1)
                    self.assertDictEqual(
                        suggestions[0],
                        {
                            'create_values': {},
                            'email': sugg_partner.email_normalized,
                            'name': sugg_partner.name,
                            'partner_id': sugg_partner.id,
                        }
                    )
                else:
                    self.assertEqual(len(suggestions), 0)

    @users("employee")
    def test_message_get_suggested_recipients_banned(self):
        """ Ban list: public partners, aliases, alias domains """
        domains = self.env['mail.alias.domain'].sudo().search([])
        domains_cc_list = []
        for domain in domains:
            domains_cc_list += [
                f'"Bounce {domain.name}" <{domain.bounce_email}>',
                f'"Catchall {domain.name}" <{domain.catchall_email}>',
                f'"Default {domain.name}" <{domain.default_from_email}>',
            ]
        tickets = self.env['mail.test.ticket.mc'].create([
            # do not propose public partners
            {
                'customer_id': self.user_public.partner_id.id,
                'name': 'Public',
            },
            # do not propose root
            {
                'customer_id': self.user_root.partner_id.id,
                'name': 'Root',
            },
            # valid, but with message containing alias domain emails
            {
                'customer_id': self.test_partner.id,
                'name': 'Valid partner + invalid domain emails in discussion',
            },
            # valid, but with message containing alias emails or partners
            {
                'customer_id': self.test_partner_archived.id,
                'name': 'Valid partner archived + invalid in discussion',
            },
        ])
        tickets[2].message_post(
            author_id=self.user_root.partner_id.id,
            body='Message with lots of invalid emails',
            incoming_email_cc=', '.join(domains_cc_list),
            message_type='email',
            subtype_id=self.env.ref('mail.mt_comment').id,
        )
        tickets[3].message_post(
            author_id=False,
            email_from=self.mail_alias_domain.bounce_email,
            body='Message with alias emails and partners',
            message_type='email',
            incoming_email_to=f'"Alias" <{self.test_aliases[0].alias_full_name}>',
            partner_ids=(self.test_partner_alias + self.test_partner_catchall).ids,
            subtype_id=self.env.ref('mail.mt_comment').id,
        )
        expected_all = [
            # nobody to suggest (no public !)
            [],
            #nobody to suggest (no root !)
            [],
            # only valid is the customer
            [
                {
                    'create_values': {},
                    'email': self.test_partner.email_normalized,
                    'name': self.test_partner.name,
                    'partner_id': self.test_partner.id,
                },
            ],
            # only valid is the customer (and not aliases nor partner with alias email)
            [
                {
                    'create_values': {},
                    'email': self.test_partner_archived.email_normalized,
                    'name': self.test_partner_archived.name,
                    'partner_id': self.test_partner_archived.id,
                },
            ],
        ]
        suggested_all = tickets._message_get_suggested_recipients_batch(no_create=True, reply_discussion=True)
        for ticket, expected in zip(tickets, expected_all, strict=True):
            with self.subTest(ticket_name=ticket.name):
                suggested = suggested_all[ticket.id]
                for suggestion, expected_sugg in zip(suggested, expected, strict=True):
                    self.assertDictEqual(suggestion, expected_sugg)

    @users("employee")
    def test_message_get_suggested_recipients_conversation(self):
        """ Test suggested recipients in a conversation based on discussion
        history: email_{cc/to} of previous messages, ... """
        test_cc_tuples = [
            ('Test Record Cc', 'test.record.cc@test.example.com'),
            ('Test Msg Cc', 'test.msg.cc@test.example.com'),
            ('Test Msg Cc 2', 'test.msg.cc.2@test.example.com'),
        ]
        test_to_tuples = [
            ('Test Msg To', 'test.msg.to@test.example.com'),
            ('Test Msg To 2', 'test.msg.to.2@test.example.com'),
        ]
        test_emails = [x[1] for x in test_cc_tuples + test_to_tuples]
        self.assertFalse(self.env['res.partner'].search([('email_normalized', 'in', test_emails)]))

        test_record = self.env['mail.test.recipients'].create({
            'email_cc': tools.mail.formataddr(test_cc_tuples[0]),
            'name': 'Test Recipients',
        })
        messages = self.env['mail.message']
        for user, post_values in [
            (self.user_root, {
                'author_id': self.user_portal.partner_id.id,
                'body': 'First incoming email',
                'email_from': self.user_portal.email_formatted,
                'incoming_email_cc': tools.mail.formataddr(test_cc_tuples[1]),
                'incoming_email_to': tools.mail.formataddr(test_to_tuples[0]),
                'message_type': 'email',
                'subtype_id': self.env.ref('mail.mt_comment').id,
            }),
            (self.user_root, {
                'body': 'Some automated email',
                'message_type': 'email_outgoing',
                'partner_ids': self.user_portal.partner_id.ids,
                'subtype_id': self.env.ref('mail.mt_comment').id,
            }),
            (self.user_employee, {
                'body': 'Salesman reply by email',
                'incoming_email_cc': tools.mail.formataddr(test_cc_tuples[2]),
                'incoming_email_to': tools.mail.formataddr(test_to_tuples[1]),
                'message_type': 'email',
                'subtype_id': self.env.ref('mail.mt_comment').id,
            }),
        ]:
            messages += test_record.with_user(user).message_post(**post_values)
        self.assertEqual(test_record.message_partner_ids, self.user_employee.partner_id)

        recipients = test_record._message_get_suggested_recipients(reply_message=messages[0], no_create=True)
        for recipient, expected in zip(recipients, [
            {  # partner first: author of message
                'create_values': {},
                'email': self.user_portal.email_normalized,
                'name': self.user_portal.name,
                'partner_id': self.user_portal.partner_id.id,
            }, {  # override of model for email_cc
                'create_values': {},
                'email': test_cc_tuples[0][1],
                'name': test_cc_tuples[0][0],
                'partner_id': False,
            }, {  # replying message to
                'create_values': {},
                'email': test_to_tuples[0][1],
                'name': test_to_tuples[0][0],
                'partner_id': False,
            }, {  # replying message  cc
                'create_values': {},
                'email': test_cc_tuples[1][1],
                'name': test_cc_tuples[1][0],
                'partner_id': False,
            },
        ], strict=True):
            with self.subTest():
                self.assertDictEqual(recipient, expected)

        recipients = test_record._message_get_suggested_recipients(reply_message=messages[1], no_create=True)
        for recipient, expected in zip(recipients, [
            {  # partner first: recipient of message
                'create_values': {},
                'email': self.user_portal.email_normalized,
                'name': self.user_portal.name,
                'partner_id': self.user_portal.partner_id.id,
            }, {  # override of model for email_cc
                'create_values': {},
                'email': test_cc_tuples[0][1],
                'name': test_cc_tuples[0][0],
                'partner_id': False,
            },  # and not author, as it is odoobot's email
        ], strict=True):
            with self.subTest():
                self.assertDictEqual(recipient, expected)

        # discussion: should be last message
        recipients = test_record._message_get_suggested_recipients(reply_discussion=True, no_create=True)
        for recipient, expected in zip(recipients, [
            {  # override of model for email_cc
                'create_values': {},
                'email': test_cc_tuples[0][1],
                'name': test_cc_tuples[0][0],
                'partner_id': False,
            }, {  # replying message to
                'create_values': {},
                'email': test_to_tuples[1][1],
                'name': test_to_tuples[1][0],
                'partner_id': False,
            }, {  # replying message  cc
                'create_values': {},
                'email': test_cc_tuples[2][1],
                'name': test_cc_tuples[2][0],
                'partner_id': False,
            },  # and not author as he is already follower
        ], strict=True):
            with self.subTest():
                self.assertDictEqual(recipient, expected)

        # check with partner creation
        recipients = test_record._message_get_suggested_recipients(reply_message=messages[0], no_create=False)
        new_partners = self.env['res.partner'].search([('email_normalized', 'in', test_emails)], order='id ASC')
        self.assertEqual(len(new_partners), 3, 'Find or create should have created 3 partners, one / email')
        new_to, new_cc_0, new_cc_1 = new_partners
        for recipient, expected in zip(recipients, [
            {  # partner first: author of message
                'create_values': {},
                'email': self.user_portal.email_normalized,
                'name': self.user_portal.name,
                'partner_id': self.user_portal.partner_id.id,
            }, {  # override of model for email_cc
                'email': test_cc_tuples[0][1],
                'name': test_cc_tuples[0][0],
                'partner_id': new_to.id,
                'create_values': {},
            }, {  # replying message to
                'email': test_to_tuples[0][1],
                'name': test_to_tuples[0][0],
                'partner_id': new_cc_0.id,
                'create_values': {},
            }, {  # replying message  cc
                'email': test_cc_tuples[1][1],
                'name': test_cc_tuples[1][0],
                'partner_id': new_cc_1.id,
                'create_values': {},
            },
        ], strict=True):
            with self.subTest():
                self.assertDictEqual(recipient, expected)

    @users("employee")
    def test_message_get_suggested_recipients_conversation_filter(self):
        """ Test sorting of messages when suggested is used in reply-all based
        on last message. """
        test_record = self.env['mail.test.recipients'].create({
            'email_cc': '"Test Cc" <test.cc.1@test.example.com>',
            'name': 'Test Recipients',
        })
        base_expected = [{
            'create_values': {},
            'email': 'test.cc.1@test.example.com',
            'name': 'Test Cc',
            'partner_id': False,
        }]
        for user, post_values, expected_add in [
            (
                self.user_employee,
                {
                    'body': 'Note with pings, to ignore',
                    'message_type': 'comment',
                    'subtype_id': self.env.ref('mail.mt_note').id,
                },
                []
            ), (
                self.user_root,
                {
                    'author_id': False,
                    'email_from': '"Outdated" <outdated@test.example.com>',
                    'body': 'Incoming (old) email',
                    'message_type': 'email',
                    'subtype_id': self.env.ref('mail.mt_comment').id,
                },
                [{
                    'create_values': {},
                    'email': 'outdated@test.example.com',
                    'name': 'Outdated',
                    'partner_id': False,
                }],
            ), (
                self.user_employee,
                {
                    'body': 'Some discussion',
                    'message_type': 'comment',
                    'partner_ids': self.user_portal.partner_id.ids,
                    'subtype_id': self.env.ref('mail.mt_comment').id,
                },
                [{
                    'create_values': {},
                    'email': self.user_portal.email_normalized,
                    'name': self.user_portal.name,
                    'partner_id': self.user_portal.partner_id.id,
                }, {
                    'create_values': {},
                    'email': self.user_employee.email_normalized,
                    'name': self.user_employee.name,
                    'partner_id': self.user_employee.partner_id.id,
                }],
            ), (
                self.user_root,
                {
                    'author_id': self.partner_employee_2.id,
                    'body': 'Some marketing email',
                    'message_type': 'email_outgoing',
                    'subtype_id': self.env.ref('mail.mt_note').id,
                },
                [{
                    'create_values': {},
                    'email': self.user_portal.email_normalized,
                    'name': self.user_portal.name,
                    'partner_id': self.user_portal.partner_id.id,
                }, {
                    'create_values': {},
                    'email': self.user_employee.email_normalized,
                    'name': self.user_employee.name,
                    'partner_id': self.user_employee.partner_id.id,
                }],
            ),
        ]:
            test_record.with_user(user).message_post(**post_values)
            test_record.message_unsubscribe(partner_ids=test_record.message_partner_ids.ids)
            suggested = test_record._message_get_suggested_recipients(reply_discussion=True, no_create=True)
            expected = base_expected + expected_add
            # as we can't use sorted directly, reorder manually, hey
            expected.sort(key=lambda item: item['partner_id'], reverse=True)
            with self.subTest(message=post_values['body']):
                for sugg, expected_sugg in zip(suggested, expected, strict=True):
                    self.assertDictEqual(sugg, expected_sugg)

    @mute_logger('openerp.addons.mail.models.mail_mail')
    @users('employee')
    def test_message_update_content(self):
        """ Test updating message content. """
        ticket_record = self.ticket_record.with_env(self.env)
        attachments = self.env['ir.attachment'].create(
            self._generate_attachments_data(2, 'mail.compose.message', 0)
        )

        # post a note
        message = ticket_record.message_post(
            attachment_ids=attachments.ids,
            body=Markup("<p>Initial Body</p>"),
            message_type="comment",
            partner_ids=self.partner_1.ids,
        )
        self.assertEqual(message.attachment_ids, attachments)
        self.assertEqual(set(message.mapped('attachment_ids.res_id')), set(ticket_record.ids))
        self.assertEqual(set(message.mapped('attachment_ids.res_model')), set([ticket_record._name]))
        self.assertEqual(message.body, "<p>Initial Body</p>")
        self.assertEqual(message.subtype_id, self.env.ref('mail.mt_note'))

        # clear the content when having attachments should show edit label
        ticket_record._message_update_content(message, body="")
        self.assertEqual(message.attachment_ids, attachments)
        self.assertEqual(message.body, Markup('<span class="o-mail-Message-edited"></span>'))
        # update the content with new attachments
        new_attachments = self.env['ir.attachment'].create(
            self._generate_attachments_data(2, 'mail.compose.message', 0)
        )
        ticket_record._message_update_content(
            message,
            body=Markup("<div>New Body</div>"),
            attachment_ids=new_attachments.ids,
        )
        self.assertEqual(message.attachment_ids, attachments + new_attachments)
        self.assertEqual(set(message.mapped('attachment_ids.res_id')), set(ticket_record.ids))
        self.assertEqual(set(message.mapped('attachment_ids.res_model')), set([ticket_record._name]))
        self.assertEqual(message.body, Markup('<div>New Body <span class="o-mail-Message-edited"></span></div>'))

        # void attachments
        ticket_record._message_update_content(
            message,
            body=Markup("<p>Another Body, void attachments</p>"),
            attachment_ids=[],
        )
        self.assertFalse(message.attachment_ids)
        self.assertFalse((attachments + new_attachments).exists())
        self.assertEqual(message.body, Markup('<p>Another Body, void attachments <span class="o-mail-Message-edited"></span></p>'))

        ticket_record._message_update_content(
            message,
            body=Markup("line1<br>edit<br>line2<br>line3"),
        )
        self.assertEqual(message.body, Markup('<p>line1 <br>edit<br>line2<br>line3<span class="o-mail-Message-edited"></span></p>'))

    @mute_logger('openerp.addons.mail.models.mail_mail')
    @users('employee')
    def test_message_update_content_check(self):
        """ Test cases where updating content should be prevented """
        ticket_record = self.ticket_record.with_env(self.env)

        message = ticket_record.message_post(
            body="<p>Initial Body</p>",
            message_type="comment",
            subtype_id=self.env.ref('mail.mt_comment').id,
        )
        ticket_record._message_update_content(message, body="<p>New Body 1</p>")

        message.sudo().write({'subtype_id': self.env.ref('mail.mt_note')})
        ticket_record._message_update_content(message, body="<p>New Body 2</p>")

        # cannot edit notifications
        for message_type in ['notification', 'user_notification', 'email', 'email_outgoing', 'auto_comment']:
            message.sudo().write({'message_type': message_type})
            with self.assertRaises(exceptions.UserError):
                ticket_record._message_update_content(message, body="<p>New Body</p>")


@tagged('mail_thread')
class TestChatterTweaks(ThreadRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestChatterTweaks, cls).setUpClass()
        cls.test_record = cls.env['mail.test.simple'].with_context(cls._test_context).create({'name': 'Test', 'email_from': 'ignasse@example.com'})

    @users('employee')
    def test_post_headers_recipients_limit(self):
        test_record = self.test_record.with_env(self.env)

        for recipients_limit, has_header in (
            (0, False),
            (2, False),  # zut alors, 2 recipients is the limit !
            (10, True),
        ):
            MailTestSimple._CUSTOMER_HEADERS_LIMIT_COUNT = recipients_limit
            with self.mock_mail_gateway(mail_unlink_sent=False), \
                    self.mock_mail_app():
                message = test_record.message_post(
                    body='With To Headers',
                    partner_ids=(self.test_partner + self.test_partner_catchall).ids,
                )

            headers = {
                'Return-Path': f'{self.mail_alias_domain.bounce_email}',
                'X-Custom': 'Done',  # model override
                'X-Odoo-Objects': f'{test_record._name}-{test_record.id}',
            }
            if has_header:
                headers['X-Msg-To-Add'] = f'{self.test_partner.email_formatted},{self.test_partner_catchall.email_formatted}'
            for recipient in self.test_partner + self.test_partner_catchall:
                self.assertMailMail(
                    recipient,
                    'sent',
                    author=self.partner_employee,
                    mail_message=message,
                    email_values={
                        'headers': headers,
                    },
                    fields_values={
                        'headers': headers,
                    },
                )

    def test_post_no_subscribe_author(self):
        original = self.test_record.message_follower_ids
        self.test_record.with_user(self.user_employee).with_context({'mail_post_autofollow_author_skip': True}).message_post(
            body='Test Body', message_type='comment', subtype_xmlid='mail.mt_comment')
        self.assertEqual(self.test_record.message_follower_ids.mapped('partner_id'), original.mapped('partner_id'))

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_no_subscribe_recipients(self):
        original = self.test_record.message_follower_ids
        self.test_record.with_user(self.user_employee).with_context({'mail_post_autofollow_author_skip': True}).message_post(
            body='Test Body', message_type='comment', subtype_xmlid='mail.mt_comment', partner_ids=[self.partner_1.id, self.partner_2.id])
        self.assertEqual(self.test_record.message_follower_ids.mapped('partner_id'), original.mapped('partner_id'))

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_subscribe_recipients(self):
        original = self.test_record.message_follower_ids
        self.test_record.with_user(self.user_employee).with_context({'mail_post_autofollow_author_skip': True, 'mail_post_autofollow': True}).message_post(
            body='Test Body', message_type='comment', subtype_xmlid='mail.mt_comment', partner_ids=[self.partner_1.id, self.partner_2.id])
        self.assertEqual(self.test_record.message_follower_ids.mapped('partner_id'), original.mapped('partner_id') | self.partner_1 | self.partner_2)

        # check _mail_thread_customer class attribute
        new_record = self.env['mail.test.thread.customer'].create({
            'customer_id': self.partner_1.id,
        })
        self.assertFalse(new_record.message_partner_ids)
        msg = new_record.with_user(self.user_employee).with_context(mail_post_autofollow_author_skip=True).message_post(
            body='Test Body', message_type='comment',
            partner_ids=(self.partner_1 + self.partner_2).ids,
            subtype_id=self.env.ref('mail.mt_comment').id,
        )
        self.assertEqual(msg.notified_partner_ids, self.partner_1 + self.partner_2)
        self.assertEqual(new_record.message_partner_ids, self.partner_1,
                         'Customer was found and added as follower automatically when pinged')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_chatter_context_cleaning(self):
        """ Test default keys are not propagated to message creation as it may
        induce wrong values for some fields, like parent_id. """
        parent = self.env['res.partner'].create({'name': 'Parent'})
        partner = self.env['res.partner'].with_context(default_parent_id=parent.id).create({'name': 'Contact'})
        self.assertFalse(partner.message_ids[-1].parent_id)

    def test_chatter_mail_create_nolog(self):
        """ Test disable of automatic chatter message at create """
        rec = self.env['mail.test.simple'].with_user(self.user_employee).with_context({'mail_create_nolog': True}).create({'name': 'Test'})
        self.flush_tracking()
        self.assertEqual(rec.message_ids, self.env['mail.message'])

        rec = self.env['mail.test.simple'].with_user(self.user_employee).with_context({'mail_create_nolog': False}).create({'name': 'Test'})
        self.flush_tracking()
        self.assertEqual(len(rec.message_ids), 1)

    def test_chatter_mail_notrack(self):
        """ Test disable of automatic value tracking at create and write """
        rec = self.env['mail.test.track'].with_user(self.user_employee).create({'name': 'Test', 'user_id': self.user_employee.id})
        self.flush_tracking()
        self.assertEqual(len(rec.message_ids), 1,
                         "A creation message without tracking values should have been posted")
        self.assertEqual(len(rec.message_ids.sudo().tracking_value_ids), 0,
                         "A creation message without tracking values should have been posted")

        rec.with_context({'mail_notrack': True}).write({'user_id': self.user_admin.id})
        self.flush_tracking()
        self.assertEqual(len(rec.message_ids), 1,
                         "No new message should have been posted with mail_notrack key")

        rec.with_context({'mail_notrack': False}).write({'user_id': self.user_employee.id})
        self.flush_tracking()
        self.assertEqual(len(rec.message_ids), 2,
                         "A tracking message should have been posted")
        self.assertEqual(len(rec.message_ids.sudo().mapped('tracking_value_ids')), 1,
                         "New tracking message should have tracking values")

    def test_chatter_tracking_disable(self):
        """ Test disable of all chatter features at create and write """
        rec = self.env['mail.test.track'].with_user(self.user_employee).with_context({'tracking_disable': True}).create({'name': 'Test', 'user_id': self.user_employee.id})
        self.flush_tracking()
        self.assertEqual(rec.sudo().message_ids, self.env['mail.message'])
        self.assertEqual(rec.sudo().mapped('message_ids.tracking_value_ids'), self.env['mail.tracking.value'])

        rec.write({'user_id': self.user_admin.id})
        self.flush_tracking()
        self.assertEqual(rec.sudo().mapped('message_ids.tracking_value_ids'), self.env['mail.tracking.value'])

        rec.with_context({'tracking_disable': False}).write({'user_id': self.user_employee.id})
        self.flush_tracking()
        self.assertEqual(len(rec.sudo().mapped('message_ids.tracking_value_ids')), 1)

        rec = self.env['mail.test.track'].with_user(self.user_employee).with_context({'tracking_disable': False}).create({'name': 'Test', 'user_id': self.user_employee.id})
        self.flush_tracking()
        self.assertEqual(len(rec.sudo().message_ids), 1,
                         "Creation message without tracking values should have been posted")
        self.assertEqual(len(rec.sudo().mapped('message_ids.tracking_value_ids')), 0,
                         "Creation message without tracking values should have been posted")

    def test_cache_invalidation(self):
        """ Test that creating a mail-thread record does not invalidate the whole cache. """
        # make a new record in cache
        record = self.env['res.partner'].new({'name': 'Brave New Partner'})
        self.assertTrue(record.name)

        # creating a mail-thread record should not invalidate the whole cache
        self.env['res.partner'].create({'name': 'Actual Partner'})
        self.assertTrue(record.name)


@tagged('mail_thread')
class TestDiscuss(MailCommon, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestDiscuss, cls).setUpClass()
        cls.test_record = cls.env['mail.test.simple'].with_context(cls._test_context).create({
            'name': 'Test',
            'email_from': 'ignasse@example.com'
        })

    @mute_logger('openerp.addons.mail.models.mail_mail')
    def test_mark_all_as_read(self):
        def _employee_crash(recordset, operation):
            """ If employee is test employee, consider they have no access on document """
            if recordset.env.uid == self.user_employee.id and not recordset.env.su:
                return recordset, lambda: exceptions.AccessError('Hop hop hop Ernest, please step back.')
            return DEFAULT

        with patch.object(MailTestSimple, '_check_access', autospec=True, side_effect=_employee_crash):
            with self.assertRaises(exceptions.AccessError):
                self.env['mail.test.simple'].with_user(self.user_employee).browse(self.test_record.ids).read(['name'])

            employee_partner = self.env['res.partner'].with_user(self.user_employee).browse(self.partner_employee.ids)

            # mark all as read clear needactions
            msg1 = self.test_record.message_post(body='Test', message_type='comment', subtype_xmlid='mail.mt_comment', partner_ids=[employee_partner.id])
            with self.assertBus(
                    [(self.cr.dbname, 'res.partner', employee_partner.id)],
                    message_items=[{
                        'type': 'mail.message/mark_as_read',
                        'payload': {
                            'message_ids': [msg1.id],
                            'needaction_inbox_counter': 0,
                        },
                    }]):
                employee_partner.env['mail.message'].mark_all_as_read(domain=[])
            na_count = employee_partner._get_needaction_count()
            self.assertEqual(na_count, 0, "mark all as read should conclude all needactions")

            # mark all as read also clear inaccessible needactions
            msg2 = self.test_record.message_post(body='Zest', message_type='comment', subtype_xmlid='mail.mt_comment', partner_ids=[employee_partner.id])
            needaction_accessible = len(employee_partner.env['mail.message'].search([['needaction', '=', True]]))
            self.assertEqual(needaction_accessible, 1, "a new message to a partner is readable to that partner")

            msg2.sudo().partner_ids = self.env['res.partner']
            employee_partner.env['mail.message'].search([['needaction', '=', True]])
            needaction_length = len(employee_partner.env['mail.message'].search([['needaction', '=', True]]))
            self.assertEqual(needaction_length, 1, "message should still be readable when notified")

            na_count = employee_partner._get_needaction_count()
            self.assertEqual(na_count, 1, "message not accessible is currently still counted")

            with self.assertBus(
                    [(self.cr.dbname, 'res.partner', employee_partner.id)],
                    message_items=[{
                        'type': 'mail.message/mark_as_read',
                        'payload': {
                            'message_ids': [msg2.id],
                            'needaction_inbox_counter': 0,
                        },
                    }]):
                employee_partner.env['mail.message'].mark_all_as_read(domain=[])
            na_count = employee_partner._get_needaction_count()
            self.assertEqual(na_count, 0, "mark all read should conclude all needactions even inacessible ones")

    def test_set_message_done_user(self):
        with self.assertSinglePostNotifications([{'partner': self.partner_employee, 'type': 'inbox'}], message_info={'content': 'Test'}):
            message = self.test_record.message_post(
                body='Test', message_type='comment', subtype_xmlid='mail.mt_comment',
                partner_ids=[self.user_employee.partner_id.id])
        message.with_user(self.user_employee).set_message_done()
        self.assertMailNotifications(message, [{'notif': [{'partner': self.partner_employee, 'type': 'inbox', 'is_read': True}]}])

    def test_message_fetch_needaction(self):
        user1 = self.env['res.users'].create({'login': 'user1', 'name': 'User 1'})
        user1.notification_type = 'inbox'
        user2 = self.env['res.users'].create({'login': 'user2', 'name': 'User 2'})
        user2.notification_type = 'inbox'
        message1 = self.test_record.with_user(self.user_admin).message_post(body='Message 1', partner_ids=[user1.partner_id.id, user2.partner_id.id])
        message2 = self.test_record.with_user(self.user_admin).message_post(body='Message 2', partner_ids=[user1.partner_id.id, user2.partner_id.id])

        # both notified users should have the 2 messages in Inbox initially
        res = self.env['mail.message'].with_user(user1)._message_fetch(domain=[['needaction', '=', True]])
        self.assertEqual(len(res["messages"]), 2)
        res = self.env['mail.message'].with_user(user2)._message_fetch(domain=[['needaction', '=', True]])
        self.assertEqual(len(res["messages"]), 2)

        # first user is marking one message as done: the other message is still Inbox, while the other user still has the 2 messages in Inbox
        message1.with_user(user1).set_message_done()
        res = self.env['mail.message'].with_user(user1)._message_fetch(domain=[['needaction', '=', True]])
        self.assertEqual(len(res["messages"]), 1)
        self.assertEqual(res["messages"][0].id, message2.id)
        res = self.env['mail.message'].with_user(user2)._message_fetch(domain=[['needaction', '=', True]])
        self.assertEqual(len(res["messages"]), 2)

    @users("employee")
    def test_unlink_notification_message(self):
        message = self.test_record.with_user(self.user_admin).message_notify(
            body='test',
            partner_ids=[self.partner_2.id],
        )
        self.assertEqual(len(message), 1, "Test message should have been posted")
        self.test_record.unlink()
        self.assertFalse(message.exists(), "Test message should have been deleted")


@tagged('mail_thread')
class TestNotification(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_record = cls.env['mail.test.simple'].create({
            'name': 'Test',
            'email_from': 'ignasse@example.com'
        })

    def test_notification_has_error_filter(self):
        """Ensure message_has_error filter is only returning threads for which
        the current user is author of a failed message."""
        message = self.test_record.with_user(self.user_admin).message_post(
            body='Test', message_type='comment', subtype_xmlid='mail.mt_comment',
            partner_ids=[self.user_employee.partner_id.id]
        )
        self.assertFalse(message.has_error)

        with self.mock_mail_gateway():
            def _connect(*args, **kwargs):
                raise Exception("Some exception")
            self.connect_mocked.side_effect = _connect

            self.user_admin.notification_type = 'email'
            message2 = self.test_record.with_user(self.user_employee).message_post(
                body='Test', message_type='comment', subtype_xmlid='mail.mt_comment',
                partner_ids=[self.user_admin.partner_id.id]
            )
            self.assertTrue(message2.has_error)
        # employee is author of message which has a failure
        threads_employee = self.test_record.with_user(self.user_employee).search([('message_has_error', '=', True)])
        self.assertEqual(len(threads_employee), 1)
        # admin is also author of a message, but it doesn't have a failure
        # and the failure from employee's message should not be taken into account for admin
        threads_admin = self.test_record.with_user(self.user_admin).search([('message_has_error', '=', True)])
        self.assertEqual(len(threads_admin), 0)


@tagged('mail_thread', 'mail_nothread')
class TestNoThread(MailCommon, TestRecipients):
    """ Specific tests for cross models thread features """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_record_nothread = cls.env['mail.test.nothread'].with_user(cls.user_employee).create({
            'customer_id': cls.partner_1.id,
            'name': 'Not A Thread',
        })
        cls.test_template = cls.env['mail.template'].create({
            'body_html': 'Hello <t t-out="object.name"/>',
            'model_id': cls.env['ir.model']._get_id('mail.test.nothread'),
            'subject': 'Subject {{ object.name }}',
            'use_default_to': True,
        })
        cls.test_attachment = cls.env['ir.attachment'].with_user(cls.user_employee).create({
            'name': 'Test Attachment',
            'datas': base64.b64encode(b'This is test attachment content'),
            'res_model': cls.test_record_nothread._name,
            'res_id': cls.test_record_nothread.id,
            'mimetype': 'text/plain',
        })

    @users('employee')
    def test_mail_composer_comment_with_template(self):
        """ This test simulates using a template, opening a composer and posting
        a message to a non-thread record, which transforms into a user notification.
        Check recipients computation works in non-thread mode. """
        record = self.test_record_nothread.with_env(self.env)
        template = self.test_template.with_env(self.env)
        mail_compose_message = self.env['mail.compose.message'].create({
            'attachment_ids': [(6, 0, [self.test_attachment.id])],
            'composition_mode': 'comment',
            'model': record._name,
            'template_id': template.id,
            'res_ids': record.ids,
        })
        with self.mock_mail_gateway():
            _mail, message = mail_compose_message._action_send_mail()
        self.assertMailNotifications(
            message,
            [{
                'content': f'Hello {record.name}',
                # not mail.thread -> automatically transformed using message_notify
                'message_type': 'user_notification',
                'notif': [{'partner': self.partner_1, 'type': 'email',}],
            }],
        )

    @users('employee')
    def test_mail_composer_mail_with_template(self):
        """ This test simulates scenarios where a required method called `_process_attachments_for_post` is missing,
        in such case composer should fallback to the method implementation in mail.thread. """
        record = self.test_record_nothread.with_env(self.env)
        template = self.test_template.with_env(self.env)
        mail_compose_message = self.env['mail.compose.message'].create({
            'composition_mode': 'mass_mail',
            'model': 'mail.test.nothread',
            'template_id': template.id,
            'res_ids': record.ids,
            'attachment_ids': [(6, 0, [self.test_attachment.id])]
        })
        with self.mock_mail_gateway():
            mail_compose_message.action_send_mail()
        self.assertEqual(self._new_mails.attachment_ids['datas'], base64.b64encode(b'This is test attachment content'),
            "The attachment was not included correctly in the sent message")

    @users('employee')
    def test_mail_template_send_mail(self):
        template = self.test_template.with_env(self.env)
        test_record = self.test_record_nothread.with_env(self.env)
        with self.mock_mail_gateway():
            template.send_mail(
                test_record.id,
                email_layout_xmlid='mail.mail_notification_light',
            )
        self.assertMailMail(
            self.partner_1,
            'outgoing',
        )

    @users('employee')
    def test_message_to_store(self):
        """ Test formatting of messages when linked to non-thread models.
        Format could be asked notably if an inbox notification due to a
        'message_notify' happens. """
        test_record = self.test_record_nothread.with_env(self.env)

        message = self.env['mail.message'].create({
            'model': test_record._name,
            'res_id': test_record.id,
        })
        formatted = Store().add(message).get_result()["mail.message"][0]
        self.assertEqual(formatted['default_subject'], test_record.name)
        self.assertEqual(formatted['record_name'], test_record.name)

        test_record.write({'name': 'Just Test'})
        message.invalidate_recordset(['record_name'])
        formatted = Store().add(message).get_result()["mail.message"][0]
        self.assertEqual(formatted['default_subject'], 'Just Test')
        self.assertEqual(formatted['record_name'], 'Just Test')

    @users('employee')
    def test_message_notify(self):
        """ Test notifying on non-thread models, using MailThread as an abstract
        class with model and res_id giving the record used for notification.

        Test default subject computation is also tested. """
        test_record = self.test_record_nothread.with_env(self.env)

        for subject in ["Test Notify", False]:
            with self.subTest():
                with self.assertPostNotifications([{
                        'content': 'Hello Paulo',
                        'email_values': {
                            'reply_to': tools.mail.formataddr((
                                self.partner_employee.name,
                                self.company_admin.catchall_email,
                            )),
                        },
                        'message_type': 'user_notification',
                        'notif': [{
                            'check_send': True,
                            'is_read': True,
                            'partner': self.partner_2,
                            'status': 'sent',
                            'type': 'email',
                        }],
                        'subtype': 'mail.mt_note',
                    }]):
                    _message = self.env['mail.thread'].message_notify(
                        body='<p>Hello Paulo</p>',
                        model=test_record._name,
                        partner_ids=self.partner_2.ids,
                        res_id=test_record.id,
                        subject=subject,
                    )

    @users('employee')
    def test_message_notify_composer(self):
        """ Test comment mode on composer which triggers a notify when model
        does not inherit from mail thread. """
        test_records, _test_partners = self._create_records_for_batch('mail.test.nothread', 2)

        test_reports = self.env['ir.actions.report'].sudo().create([
            {
                'name': 'Test Report on Mail Test Ticket',
                'model': test_records._name,
                'print_report_name': "'TestReport for %s' % object.name",
                'report_type': 'qweb-pdf',
                'report_name': 'test_mail.mail_test_ticket_test_template',
            }, {
                'name': 'Test Report 2 on Mail Test Ticket',
                'model': test_records._name,
                'print_report_name': "'TestReport2 for %s' % object.name",
                'report_type': 'qweb-pdf',
                'report_name': 'test_mail.mail_test_ticket_test_template_2',
            }
        ])
        test_template = self.env['mail.template'].create({
            'auto_delete': True,
            'body_html': '<p>TemplateBody <t t-esc="object.name"></t></p>',
            'email_from': '{{ (user.email_formatted) }}',
            'email_to': '',
            'mail_server_id': self.mail_server_domain.id,
            'partner_to': '{{ object.customer_id.id if object.customer_id else "" }}',
            'name': 'TestTemplate',
            'model_id': self.env['ir.model']._get(test_records._name).id,
            'reply_to': '{{ ctx.get("custom_reply_to") or "info@test.example.com" }}',
            'report_template_ids': [(6, 0, test_reports.ids)],
            'scheduled_date': '{{ (object.create_date or datetime.datetime(2022, 12, 26, 18, 0, 0)) + datetime.timedelta(days=2) }}',
            'subject': 'TemplateSubject {{ object.name }}',
        })
        attachment_data = self._generate_attachments_data(2, test_template._name, test_template.id)
        test_template.write({'attachment_ids': [(0, 0, a) for a in attachment_data]})

        ctx = {
            'default_composition_mode': 'comment',
            'default_model': test_records._name,
            'default_res_domain': [('id', 'in', test_records.ids)],
            'default_template_id': test_template.id,
        }
        # open a composer and run it in comment mode
        composer_form = Form(self.env['mail.compose.message'].with_context(ctx))
        composer = composer_form.save()

        with self.mock_mail_gateway(mail_unlink_sent=False), self.mock_mail_app():
            _, messages = composer._action_send_mail()

        self.assertEqual(len(messages), 2)
        for record, message in zip(test_records, messages, strict=True):
            self.assertEqual(
                sorted(message.mapped('attachment_ids.name')),
                sorted(['AttFileName_00.txt', 'AttFileName_01.txt',
                        f'TestReport2 for {record.name}.html',
                        f'TestReport for {record.name}.html'])
            )
        self.assertEqual(len(messages.attachment_ids), 8, 'No attachments should be shared')

    @users('employee')
    def test_message_notify_norecord(self):
        """ Test notifying on no record, just using the abstract model itself. """
        with self.assertPostNotifications([{
                'content': 'Hello Paulo',
                'email_values': {
                    'reply_to': tools.mail.formataddr((
                        self.partner_employee.name,
                        self.company_admin.catchall_email,
                    )),
                    'subject': 'Test Notify',
                },
                'message_type': 'user_notification',
                'notif': [{
                    'check_send': True,
                    'is_read': True,
                    'partner': self.partner_2,
                    'status': 'sent',
                    'type': 'email',
                }],
                'subtype': 'mail.mt_note',
            }]):
            _message = self.env['mail.thread'].message_notify(
                body=Markup('<p>Hello Paulo</p>'),
                partner_ids=self.partner_2.ids,
                subject='Test Notify',
            )
