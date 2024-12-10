# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from unittest.mock import patch
from unittest.mock import DEFAULT
import base64

from odoo import exceptions
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.test_mail.models.test_mail_models import MailTestSimple
from odoo.addons.test_mail.tests.common import TestRecipients
from odoo.addons.mail.tools.discuss import Store
from odoo.tests import Form, tagged, users
from odoo.tools import mute_logger


@tagged('mail_thread', 'mail_tools')
class TestAPI(MailCommon, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_partner = cls.env['res.partner'].create({
            'email': '"Test External" <test.external@example.com>',
            'mobile': '+32455001122',
            'name': 'Test External',
        })
        cls.ticket_record = cls.env['mail.test.ticket.mc'].create({
            'company_id': cls.user_employee.company_id.id,
            'email_from': '"Paulette Vachette" <paulette@test.example.com>',
            'mobile_number': '+32455998877',
            'phone_number': 'wrong',
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
                'mobile_number': '+32455000001',
                'name': 'Wrong email',
            }, {
                'email_from': False,
                'name': 'Falsy email',
            }, {
                'email_from': f'"Other Name" <{cls.test_partner.email_normalized}>',
                'name': 'Test Partner Email',
            },
        ])

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
        ticket_record._message_update_content(message, "Hello <R&D/>")
        self.assertEqual(message.body, Markup('<p>Hello &lt;R&amp;D/&gt;<span class="o-mail-Message-edited"></span></p>'))

    @users('employee')
    def test_mail_partner_find_from_emails(self):
        """ Test '_mail_find_partner_from_emails'. Multi mode is mainly targeting
        finding or creating partners based on record information or message
        history. """
        existing_partners = self.env['res.partner'].sudo().search([])
        tickets = self.ticket_records.with_user(self.env.user)
        self.assertEqual(len(tickets), 6)
        res = tickets._mail_find_partner_from_emails(
            [ticket.email_from for ticket in tickets],
            force_create=True,
        )
        self.assertEqual(len(tickets), len(res))

        # fetch partners that should have been created
        new = self.env['res.partner'].search([('email_normalized', '=', 'paulette@test.example.com')])
        self.assertEqual(len(new), 2, 'FIXME: created twice because does not check for duplicated when creating')
        # self.assertEqual(len(new), 1, 'Should have created once the customer, even if found in various duplicates')
        self.assertNotIn(new, existing_partners)
        new_wrong = self.env['res.partner'].search([('email', '=', 'wrong')])
        self.assertFalse(new_wrong)
        # self.assertEqual(len(new_wrong), 1, 'Should have created once the wrong email')
        # self.assertNotIn(new, new_wrong)
        new_multi = self.env['res.partner'].search([('email_normalized', '=', 'multi@test.example.com')])
        self.assertEqual(len(new_multi), 1, 'Should have created a based for multi email, using the first found email')
        self.assertNotIn(new, new_multi)

        # assert results: found / create partners and their values (if applies)
        record_customer_values = {
            # 'company_id': self.user_employee.company_id,  # FIXME: does not respect customer info propagation
            'email': 'paulette@test.example.com',
            # 'mobile': '+32455998877',
            'name': 'Paulette Vachette',
            # 'phone': 'wrong',
        }
        expected_all = [
            (new[1], [record_customer_values]),  # FIXME: duplicate, wrong name, ...
            (new[0], [{'email': 'paulette@test.example.com', 'name': 'Maybe Paulette'}]),  # FIXME: duplicate, wrong name, ...
            (new_multi, [{  # not the actual record customer hence no mobile / phone, see _get_customer_information
                # 'company_id': self.user_employee.company_id,
                'email': 'multi@test.example.com',
                'mobile': False,
                'name': 'Multi Customer',
                'phone': False,
            }]),
            (new_wrong, [{'name': 'wrong', 'email': 'wrong', 'company_id': self.env['res.company']}]),
            (self.env['res.partner'], [{}]),
            (self.test_partner, [{}]),
        ]
        for partners, (exp_partners, exp_values_list) in zip(res, expected_all):
            with self.subTest(ticket_name=exp_partners.name):
                self.assertEqual(partners, exp_partners)
                for partner, exp_values in zip(partners, exp_values_list):
                    for fname, fvalue in exp_values.items():
                        self.assertEqual(partners[fname], fvalue)

    @users('employee')
    def test_mail_partner_find_from_emails_ordering(self):
        """ Test '_mail_find_partner_from_emails' on a single record, to test notably
        ordering and filtering. """
        self.user_employee.write({'company_ids': [(4, self.company_2.id)]})
        # create a mess, mix of portal / internal users + customer, to test ordering
        portal_user, internal_user = self.env['res.users'].sudo().create([
            {
                'company_id': self.env.user.company_id.id,
                'email': 'test.ordering@test.example.com',
                'groups_id': [(4, self.env.ref('base.group_portal').id)],
                'login': 'order_portal',
                'name': 'Portal Test User for ordering',
            }, {
                'company_id': self.env.user.company_id.id,
                'email': 'test.ordering@test.example.com',
                'groups_id': [(4, self.env.ref('base.group_user').id)],
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
            # various partners: should be id ASC FIXME
            # (dupe_partners[1] + dupe_partners[3], self.env['res.partner'], dupe_partners[1]),
            (dupe_partners[1] + dupe_partners[3], self.env['res.partner'], dupe_partners[3]),  # complete_name asc -> remove me when fixed
            # involving matching company check: matching company wins
            (dupe_partners, self.env['res.partner'], dupe_partners[2]),
            # users > partner
            (portal_user.partner_id + dupe_partners, self.env['res.partner'], portal_user.partner_id),
            # internal user > any other user FIXME not correctly computed
            # (portal_user.partner_id + internal_user.partner_id + dupe_partners, self.env['res.partner'], internal_user.partner_id),
            (portal_user.partner_id + internal_user.partner_id + dupe_partners, self.env['res.partner'], portal_user.partner_id),  # internal user > any other user -> remove me when fixed
            # follower > any other thing
            (internal_user.partner_id + dupe_partners, dupe_partners[0], dupe_partners[0]),
        ]:
            with self.subTest(names=active_partners.mapped('name'), followers=followers.mapped('name')):
                # removes (through deactivating) some partners to check ordering
                (portal_user + internal_user).filtered(lambda u: u.partner_id not in active_partners).active = False
                (all_partners - active_partners).active = False
                self.ticket_record.message_subscribe(followers.ids)

                ticket = self.ticket_record.with_user(self.env.user)
                res = ticket._mail_find_partner_from_emails(
                    [ticket.email_from, 'test.ordering@test.example.com'],
                    force_create=False,
                    records=ticket,
                )

                # new - linked to record: not existing, hence not found
                self.assertFalse(res[0])
                self.assertEqual(res[1], expected, f'Found {res[1].name} instead of {expected.name}')

                all_partners.active = True
                (portal_user + internal_user).active = True
                self.ticket_record.message_unsubscribe(followers.ids)

    @users('employee')
    def test_mail_partner_find_from_emails_record(self):
        """ On a given record, give several emails and check it is effectively
        based on record information. """
        ticket = self.ticket_record.with_user(self.env.user)
        res = ticket._mail_find_partner_from_emails(
            [
                'raoul@test.example.com',
                ticket.email_from,
                self.test_partner.email,
            ],
            force_create=True,
        )

        # new - extra email
        other = res[0]
        # self.assertEqual(other.company_id, self.user_employee.company_id)
        self.assertEqual(other.email, "raoul@test.example.com")
        self.assertFalse(other.mobile)
        self.assertEqual(other.name, "raoul@test.example.com")
        # new - linked to record
        customer = res[1]
        # self.assertEqual(customer.company_id, self.user_employee.company_id)
        self.assertEqual(customer.email, "paulette@test.example.com")
        # self.assertEqual(customer.mobile, "+32455998877", "Should come from record, see '_get_customer_information'")
        self.assertEqual(customer.name, "Paulette Vachette")
        # found
        self.assertEqual(res[2], self.test_partner)

    @users('employee')
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
        with self.assertQueryCount(20):
            defaults_withcc = test_records.with_context(mail_recipients_include_cc=True)._message_get_default_recipients()
            defaults_withoutcc = test_records.with_context(mail_recipients_include_cc=False)._message_get_default_recipients()
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
        ]):
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

    @users("employee")
    def test_message_get_suggested_recipients(self):
        """ Test default creation values returned for suggested recipient. """
        ticket = self.ticket_record.with_user(self.env.user)
        ticket.message_unsubscribe(ticket.user_id.partner_id.ids)
        suggestions = ticket._message_get_suggested_recipients()
        self.assertEqual(len(suggestions), 2)
        for suggestion, expected in zip(suggestions, [{
            'email': self.user_employee.email_normalized,
            'lang': None,
            'name': self.user_employee.name,
            'partner_id': self.partner_employee.id,
            'reason': 'Responsible',
        }, {
            'create_values': {'mobile': '+32455998877', 'phone': 'wrong'},
            'email': '"Paulette Vachette" <paulette@test.example.com>',
            'lang': None,
            'name': '"Paulette Vachette" <paulette@test.example.com>',
            'reason': 'Customer Email',
        }]):
            self.assertDictEqual(suggestion, expected)

        # existing partner not linked -> should propose it
        ticket_partner_email = self.env['mail.test.ticket.mc'].create({
            'customer_id': False,
            'email_from': self.test_partner.email_formatted,
            'mobile_number': '+33199001015',
            'user_id': self.env.user.id,  # should not be proposed, already follower
        })
        # existing partner -> should propose it
        ticket_partner = self.env['mail.test.ticket.mc'].create({
            'customer_id': self.test_partner.id,
            'email_from': self.test_partner.email_formatted,
        })
        for ticket in ticket_partner_email + ticket_partner:
            with self.subTest(ticket=ticket.name):
                suggestions = ticket_partner_email._message_get_suggested_recipients()
                self.assertEqual(len(suggestions), 1)
                self.assertDictEqual(
                    suggestions[0],
                    {
                        'email': self.test_partner.email_normalized,
                        'lang': None,
                        'name': self.test_partner.name,
                        'partner_id': self.test_partner.id,
                        'reason': 'Customer Email',
                    }
                )

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
        ticket_record._message_update_content(
            message, "",
        )
        self.assertEqual(message.attachment_ids, attachments)
        self.assertEqual(message.body, Markup('<span class="o-mail-Message-edited"></span>'))
        # update the content with new attachments
        new_attachments = self.env['ir.attachment'].create(
            self._generate_attachments_data(2, 'mail.compose.message', 0)
        )
        ticket_record._message_update_content(
            message, Markup("<p>New Body</p>"),
            attachment_ids=new_attachments.ids
        )
        self.assertEqual(message.attachment_ids, attachments + new_attachments)
        self.assertEqual(set(message.mapped('attachment_ids.res_id')), set(ticket_record.ids))
        self.assertEqual(set(message.mapped('attachment_ids.res_model')), set([ticket_record._name]))
        self.assertEqual(message.body, Markup('<p>New Body</p><span class="o-mail-Message-edited"></span>'))

        # void attachments
        ticket_record._message_update_content(
            message, Markup("<p>Another Body, void attachments</p>"),
            attachment_ids=[]
        )
        self.assertFalse(message.attachment_ids)
        self.assertFalse((attachments + new_attachments).exists())
        self.assertEqual(message.body, Markup('<p>Another Body, void attachments</p><span class="o-mail-Message-edited"></span>'))

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
        ticket_record._message_update_content(
            message, "<p>New Body 1</p>"
        )

        message.sudo().write({'subtype_id': self.env.ref('mail.mt_note')})
        ticket_record._message_update_content(
            message, "<p>New Body 2</p>"
        )

        # cannot edit notifications
        for message_type in ['notification', 'user_notification', 'email', 'email_outgoing', 'auto_comment']:
            message.sudo().write({'message_type': message_type})
            with self.assertRaises(exceptions.UserError):
                ticket_record._message_update_content(
                    message, "<p>New Body</p>"
                )


@tagged('mail_thread')
class TestChatterTweaks(MailCommon, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestChatterTweaks, cls).setUpClass()
        cls.test_record = cls.env['mail.test.simple'].with_context(cls._test_context).create({'name': 'Test', 'email_from': 'ignasse@example.com'})

    def test_post_no_subscribe_author(self):
        original = self.test_record.message_follower_ids
        self.test_record.with_user(self.user_employee).with_context({'mail_create_nosubscribe': True}).message_post(
            body='Test Body', message_type='comment', subtype_xmlid='mail.mt_comment')
        self.assertEqual(self.test_record.message_follower_ids.mapped('partner_id'), original.mapped('partner_id'))

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_no_subscribe_recipients(self):
        original = self.test_record.message_follower_ids
        self.test_record.with_user(self.user_employee).with_context({'mail_create_nosubscribe': True}).message_post(
            body='Test Body', message_type='comment', subtype_xmlid='mail.mt_comment', partner_ids=[self.partner_1.id, self.partner_2.id])
        self.assertEqual(self.test_record.message_follower_ids.mapped('partner_id'), original.mapped('partner_id'))

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_subscribe_recipients(self):
        original = self.test_record.message_follower_ids
        self.test_record.with_user(self.user_employee).with_context({'mail_create_nosubscribe': True, 'mail_post_autofollow': True}).message_post(
            body='Test Body', message_type='comment', subtype_xmlid='mail.mt_comment', partner_ids=[self.partner_1.id, self.partner_2.id])
        self.assertEqual(self.test_record.message_follower_ids.mapped('partner_id'), original.mapped('partner_id') | self.partner_1 | self.partner_2)

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
            self._reset_bus()
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

            self._reset_bus()
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
        # TDE TODO: it seems bus notifications could be checked

    def test_set_star(self):
        msg = self.test_record.with_user(self.user_admin).message_post(body='My Body', subject='1')
        msg_emp = self.env['mail.message'].with_user(self.user_employee).browse(msg.id)

        # Admin set as starred
        msg.toggle_message_starred()
        self.assertTrue(msg.starred)

        # Employee set as starred
        msg_emp.toggle_message_starred()
        self.assertTrue(msg_emp.starred)

        # Do: Admin unstars msg
        msg.toggle_message_starred()
        self.assertFalse(msg.starred)
        self.assertTrue(msg_emp.starred)

    def test_inbox_message_fetch_needaction(self):
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

    @users("employee")
    def test_unlink_notification_message(self):
        channel = self.env['discuss.channel'].create({'name': 'testChannel'})
        channel.with_user(self.user_admin).message_notify(
            body='test',
            partner_ids=[self.partner_2.id],
        )
        channel_message = self.env['mail.message'].sudo().search([('model', '=', 'discuss.channel'), ('res_id', 'in', channel.ids)])
        self.assertEqual(len(channel_message), 1, "Test message should have been posted")
        channel.sudo().unlink()
        remaining_message = channel_message.exists()
        self.assertEqual(len(remaining_message), 0, "Test message should have been deleted")


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

    @users('employee')
    def test_mail_template_send_mail(self):
        template = self.env['mail.template'].create({
            'model_id': self.env['ir.model']._get_id('mail.test.nothread'),
            'use_default_to': True,
        })
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
    def test_mail_sending_on_non_thread_model(self):
        """ This test simulates scenarios where a required method called `_process_attachments_for_post` is missing,
        in such case composer should fallback to the method implementation in mail.thread. """
        record = self.env['mail.test.nothread'].sudo().create({
            'name': 'Test Model Missing Method',
        })
        attachment = self.env['ir.attachment'].create({
            'name': 'Test Attachment',
            'datas': base64.b64encode(b'This is test attachment content'),
            'res_model': 'mail.test.nothread',
            'res_id': record.id,
            'mimetype': 'text/plain',
        })
        template = self.env['mail.template'].create({
            'name': 'TestTemplate',
            'model_id': self.env['ir.model']._get_id('mail.test.nothread'),
        })
        mail_compose_message = self.env['mail.compose.message'].create({
            'composition_mode': 'mass_mail',
            'model': 'mail.test.nothread',
            'template_id': template.id,
            'res_ids': record.ids,
            'attachment_ids': [(6, 0, [attachment.id])]
        })
        with self.mock_mail_gateway():
            mail_compose_message.action_send_mail()
        self.assertEqual(self._new_mails.attachment_ids['datas'], base64.b64encode(b'This is test attachment content'),
            "The attachment was not included correctly in the sent message")

    @users('employee')
    def test_message_to_store(self):
        """ Test formatting of messages when linked to non-thread models.
        Format could be asked notably if an inbox notification due to a
        'message_notify' happens. """
        test_record = self.test_record_nothread.with_env(self.env)

        message = self.env['mail.message'].create({
            'model': test_record._name,
            'record_name': 'Not used in message _to_store',
            'res_id': test_record.id,
        })
        formatted = Store(message, for_current_user=True).get_result()["mail.message"][0]
        self.assertEqual(formatted['default_subject'], test_record.name)
        self.assertEqual(formatted['record_name'], test_record.name)

        test_record.write({'name': 'Just Test'})
        formatted = Store(message, for_current_user=True).get_result()["mail.message"][0]
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
                            'reply_to': self.company_admin.catchall_formatted,
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
        for record, message in zip(test_records, messages):
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
                    'reply_to': self.company_admin.catchall_formatted,
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
