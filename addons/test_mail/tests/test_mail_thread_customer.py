# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.test_mail.data.test_mail_data import MAIL_TEMPLATE
from odoo.addons.test_mail.tests.common import TestMailCommon, TestRecipients
from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import formataddr, mute_logger


@tagged('mail_thread_customer')
class TestMailThreadCustomer(TestMailCommon, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestMailThreadCustomer, cls).setUpClass()

        # ensure employee can create partners, necessary for templates
        cls.user_employee.write({
            'groups_id': [(4, cls.env.ref('base.group_partner_manager').id)],
        })

        # public user and its partner, to ensure we limit its use
        cls.user_public = mail_new_test_user(cls.env, login='bert', groups='base.group_public', name='Bert Tartignole')
        cls.partner_public = cls.user_public.partner_id

        # test records and alias for mailgateway
        cls.test_record = cls.env['mail.test.customer'].create({
            'name': 'Test Customer Record',
        })
        cls.alias = cls.env['mail.alias'].create({
            'alias_name': 'test.customer',
            'alias_user_id': False,
            'alias_model_id': cls.env['ir.model']._get('mail.test.customer').id,
            'alias_contact': 'everyone',
        })

        # update customer to have "real" email formatting that tends to create issues
        cls.partner_1.write({
            'email': 'Valid Lelitre <%s>' % cls.partner_1.email_normalized
        })
        cls.partner_from = '"FormattedContact" <%s>' % cls.partner_1.email_normalized
        cls.email_from = 'Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>'

        cls._init_mail_gateway()

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_gateway_new(self):
        """ When going through mail gateway, name and email fields are updated
        with email details when email is not recognized. """
        # dupe partner, just test "similar" email is not taken into account
        self.env['res.partner'].create({
            'name': 'Dupe Partner',
            'email': 'test.test.sylvie.lelitre@agrolait.com'
        })

        test_record = self.format_and_process(
            MAIL_TEMPLATE, self.email_from, 'test.customer@test.com',
            subject='CustomerThread',
            cc='cc1@example.com, cc2@example.com',
            target_model='mail.test.customer')

        # record created with basic info from email
        self.assertEqual(test_record.customer_id, self.env['res.partner'])
        self.assertEqual(test_record.email_from, formataddr(('Sylvie Lelitre', 'test.sylvie.lelitre@agrolait.com')))
        self.assertEqual(test_record.message_partner_ids, self.env['res.partner'])
        self.assertEqual(test_record.name, 'CustomerThread')
        self.assertEqual(test_record.user_id, self.env['res.users'])

        # should have gateway message
        new_message = test_record.message_ids[0]
        self.assertFalse(new_message.author_id)
        self.assertEqual(new_message.email_from, formataddr(('Sylvie Lelitre', 'test.sylvie.lelitre@agrolait.com')))
        self.assertFalse(new_message.partner_ids)
        self.assertEqual(new_message.subject, "CustomerThread")

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_gateway_new_customer(self):
        """ When going through mail gateway, name and email fields are updated
        with email details when email is not recognized. """
        # dupe partner, just test "similar" email is not taken into account
        self.env['res.partner'].create({
            'name': 'Dupe Partner',
            'email': 'test.test.sylvie.lelitre@agrolait.com'
        })

        test_record = self.format_and_process(
            MAIL_TEMPLATE, self.partner_from, 'test.customer@test.com',
            subject='CustomerThread',
            cc='cc1@example.com, cc2@example.com',
            target_model='mail.test.customer')

        # record created with customer info from email
        self.assertEqual(test_record.customer_id, self.partner_1)
        self.assertEqual(test_record.email_from, self.partner_from)
        self.assertEqual(test_record.message_partner_ids, self.partner_1)
        self.assertEqual(test_record.name, 'CustomerThread')
        self.assertEqual(test_record.user_id, self.env['res.users'])

        # should have gateway message
        new_message = test_record.message_ids[0]
        self.assertEqual(new_message.author_id, self.partner_1)
        self.assertEqual(new_message.email_from, self.partner_from)
        self.assertFalse(new_message.partner_ids)
        self.assertEqual(new_message.subject, "CustomerThread")

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('employee')
    def test_post_subscribe(self):
        """ Test posting on document with customer as recipient adds him as
        follower. """
        test_record = self.env['mail.test.customer'].browse(self.test_record.ids)
        test_record.message_post(
            body='<p>Test Body</p>',
            message_type='comment',
            subtype_id=self.env.ref('mail.mt_comment').id,
        )
        self.assertEqual(test_record.message_partner_ids, self.env.user.partner_id)

        # custome set subscribes him
        test_record.write({'customer_id': self.partner_1.id})
        self.assertEqual(test_record.message_partner_ids, self.env.user.partner_id + self.partner_1)

        # customer is removed from followers for some reason
        test_record.message_unsubscribe(self.partner_1.ids)
        self.assertEqual(test_record.message_partner_ids, self.env.user.partner_id)

        # writing to customer adds him back
        test_record.message_post(
            body='<p>Test Body</p>',
            message_type='comment',
            partner_ids=self.partner_1.ids,
            subtype_id=self.env.ref('mail.mt_comment').id,
        )
        self.assertEqual(test_record.customer_id, self.partner_1)
        self.assertEqual(test_record.email_from, self.partner_1.email, "Email is synchronized with customer if missing")
        self.assertEqual(test_record.message_partner_ids, self.env.user.partner_id + self.partner_1)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('employee')
    def test_post_update_customer(self):
        """ Test creating a partner based on a record's email_from updates record
        having this email and no partner. This ensure we update customer information
        and adds him as follower. """
        test_record = self.env['mail.test.customer'].create({
            'name': 'CustomerThread',
            'email_from': self.email_from,
        })
        self.assertFalse(test_record.customer_id)
        self.assertEqual(test_record.email_from, self.email_from)
        self.assertEqual(test_record.message_partner_ids, self.env.user.partner_id)

        # dupe partner, just test "similar" email is not taken into account
        partner_dupe = self.env['res.partner'].create({
            'name': 'Dupe Partner',
            'email': 'test.test.sylvie.lelitre@agrolait.com'
        })

        # same email_from
        record_email = self.env['mail.test.customer'].create({
            'name': 'CustomerThread 2',
            'email_from': 'test.sylvie.lelitre@agrolait.com',
        })
        record_email_formatted = self.env['mail.test.customer'].create({
            'name': 'CustomerThread 3',
            'email_from': formataddr(('Another Name', 'test.sylvie.lelitre@agrolait.com')),
        })
        # not same email_from
        record_email_other = self.env['mail.test.customer'].create({
            'name': 'CustomerThread Similar',
            'email_from': 'testtest.sylvie.lelitre@agrolait.com',
        })
        self.assertEqual(record_email.message_partner_ids, self.env.user.partner_id)
        self.assertEqual(record_email_formatted.message_partner_ids, self.env.user.partner_id)
        self.assertEqual(record_email_other.message_partner_ids, self.env.user.partner_id)

        # through chatter a reply is done, creating a customer thanks to template
        test_record.message_post_with_template(
            self.env.ref('test_mail.mail_template_data_mail_test_customer').id,
            email_layout_xmlid="mail.mail_notification_light",
            message_type="comment",
        )
        new_message = test_record.message_ids[0]
        new_partner = self.env['res.partner'].search([('email_normalized', '=', 'test.sylvie.lelitre@agrolait.com')])
        self.assertTrue(new_partner != partner_dupe)
        # check message information
        self.assertEqual(new_message.partner_ids, new_partner)
        self.assertEqual(new_message.subject, "Message on %s" % test_record.name)
        # records should have been updated with customer thanks for post post hook
        self.assertEqual(test_record.customer_id, new_partner)
        self.assertEqual(test_record.message_partner_ids, self.env.user.partner_id + new_partner)
        self.assertEqual(record_email.customer_id, new_partner)
        self.assertEqual(record_email.message_partner_ids, self.env.user.partner_id + new_partner)
        # some records are not recognized: due to formatting, and different email
        self.assertFalse(record_email_formatted.customer_id)
        self.assertEqual(record_email_formatted.message_partner_ids, self.env.user.partner_id)
        self.assertFalse(record_email_other.customer_id)
        self.assertEqual(record_email_other.message_partner_ids, self.env.user.partner_id)

    @users('employee')
    def test_suggested_recipients(self):
        """ Test suggested recipients containing email and customer """
        test_record = self.env['mail.test.customer'].create({
            'name': 'Test Customer Record',
            'customer_id': self.partner_1.id,
        })
        self.assertEqual(test_record.message_partner_ids, self.env.user.partner_id + self.partner_1)
        res = test_record._message_get_suggested_recipients()[test_record.id]
        self.assertEqual(res, [], "No suggested recipient as customer is already follower")

        test_record.write({
            'user_id': self.user_admin.id,
        })
        self.assertEqual(test_record.message_partner_ids, self.env.user.partner_id + self.partner_1 + self.partner_admin)
        res = test_record._message_get_suggested_recipients()[test_record.id]
        self.assertEqual(res, [], "No suggested recipient as customer + responsible are already followers")

        # suggestions: responsible and customer (prior to email)
        test_record.message_unsubscribe((self.partner_1 + self.partner_admin).ids)
        res = test_record._message_get_suggested_recipients()[test_record.id]
        self.assertEqual(len(res), 2, 'Should contain: responsible + customer')
        for partner, reason in [(self.partner_admin, 'Responsible'), (self.partner_1, 'Customer')]:
            self.assertIn((partner.id, partner.email_formatted, reason), res)

        # suggestions: when not having a customer, let us use email
        test_record.write({
            'customer_id': False,
            'email_from': '"Robert Carcajou <robert@test.example.com',
        })
        res = test_record._message_get_suggested_recipients()[test_record.id]
        self.assertEqual(len(res), 2, 'Should contain: responsible + email')
        self.assertIn((self.partner_admin.id, self.partner_admin.email_formatted, 'Responsible'), res)
        self.assertIn((False, '"Robert Carcajou <robert@test.example.com', 'Customer Email'), res)

        # suggestions: public partner should not be suggested (indicate website user)
        test_record.write({
            'customer_id': self.partner_public.id,
        })
        res = test_record._message_get_suggested_recipients()[test_record.id]
        self.assertEqual(len(res), 2, 'Should contain: responsible + email')
        self.assertIn((self.partner_admin.id, self.partner_admin.email_formatted, 'Responsible'), res)
        self.assertIn((False, '"Robert Carcajou <robert@test.example.com', 'Customer Email'), res)

        test_record.write({'email_from': False})
        res = test_record._message_get_suggested_recipients()[test_record.id]
        self.assertEqual([(self.partner_admin.id, self.partner_admin.email_formatted, 'Responsible')], res)

    @users('employee')
    def test_synchronize_create(self):
        """ Test creating with a customer adds him in followers """
        test_record = self.env['mail.test.customer'].create({
            'name': 'Test Customer Record',
            'customer_id': self.partner_1.id,
        })
        self.assertEqual(test_record.message_partner_ids, self.env.user.partner_id + self.partner_1)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('employee')
    def test_synchronize_public(self):
        """ Test public customers (website users) are not synchronized """
        test_record = self.env['mail.test.customer'].create({
            'name': 'Test Customer Record',
            'customer_id': self.partner_public.id,
        })
        self.assertEqual(test_record.message_partner_ids, self.env.user.partner_id)

        test_record.message_post(
            body='<p>Test Body</p>',
            message_type='comment',
            partner_ids=self.partner_1.ids,
            subtype_id=self.env.ref('mail.mt_comment').id,
        )
        self.assertEqual(test_record.message_partner_ids, self.env.user.partner_id)

    @users('employee')
    def test_synchronize_write(self):
        """ Test setting customer adds him in followers """
        test_record = self.env['mail.test.customer'].browse(self.test_record.ids)
        self.assertFalse(test_record.message_partner_ids)

        test_record.write({'customer_id': self.partner_1.id})
        self.assertEqual(test_record.message_partner_ids, self.partner_1)
