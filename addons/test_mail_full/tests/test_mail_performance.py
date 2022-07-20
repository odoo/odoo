# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.test_mail.tests.test_performance import BaseMailPerformance
from odoo.tests.common import users, warmup
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('mail_performance', 'post_install', '-at_install')
class TestMailPerformance(BaseMailPerformance):

    @classmethod
    def setUpClass(cls):
        super(TestMailPerformance, cls).setUpClass()

        # users / followers
        cls.user_emp_email = mail_new_test_user(
            cls.env,
            company_id=cls.user_admin.company_id.id,
            company_ids=[(4, cls.user_admin.company_id.id)],
            email='user.emp.email@test.example.com',
            login='user_emp_email',
            groups='base.group_user,base.group_partner_manager',
            name='Emmanuel Email',
            notification_type='email',
            signature='--\nEmmanuel',
        )
        cls.user_portal = mail_new_test_user(
            cls.env,
            company_id=cls.user_admin.company_id.id,
            company_ids=[(4, cls.user_admin.company_id.id)],
            email='user.portal@test.example.com',
            login='user_portal',
            groups='base.group_portal',
            name='Paul Portal',
        )
        cls.customers = cls.env['res.partner'].create([
            {'country_id': cls.env.ref('base.be').id,
             'email': 'customer.full.test.1@example.com',
             'name': 'Test Full Customer 1',
             'mobile': '0456112233',
             'phone': '0456112233',
            },
            {'country_id': cls.env.ref('base.be').id,
             'email': 'customer.full.test.2@example.com',
             'name': 'Test Full Customer 2',
             'mobile': '0456223344',
             'phone': '0456112233',
            },
        ])

        # record
        cls.record_container = cls.env['mail.test.container.mc'].create({
            'alias_name': 'test-alias',
            'customer_id': cls.customer.id,
            'name': 'Test Container',
        })
        cls.record_ticket = cls.env['mail.test.ticket.mc'].create({
            'email_from': 'email.from@test.example.com',
            'container_id': cls.record_container.id,
            'customer_id': False,
            'name': 'Test Ticket',
            'user_id': cls.user_emp_email.id,
        })
        cls.record_ticket.message_subscribe(cls.customers.ids + cls.user_admin.partner_id.ids + cls.user_portal.partner_id.ids)

    def test_initial_values(self):
        """ Simply ensure some values through all tests """
        record_ticket = self.env['mail.test.ticket.mc'].browse(self.record_ticket.ids)
        self.assertEqual(record_ticket.message_partner_ids,
                         self.user_emp_email.partner_id + self.user_admin.partner_id + self.customers + self.user_portal.partner_id)
        self.assertEqual(len(record_ticket.message_ids), 1)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('employee')
    @warmup
    def test_message_post_w_followers(self):
        """ Aims to cover as much features of message_post as possible """
        record_ticket = self.env['mail.test.ticket.mc'].browse(self.record_ticket.ids)
        attachments = self.env['ir.attachment'].create(self.test_attachments_vals)

        with self.assertQueryCount(employee=68):  # tmf: 61 / com: 68
            new_message = record_ticket.message_post(
                attachment_ids=attachments.ids,
                body='<p>Test Content</p>',
                message_type='comment',
                subject='Test Subject',
                subtype_xmlid='mail.mt_comment',
            )

        self.assertEqual(
            new_message.notified_partner_ids,
            self.user_emp_email.partner_id + self.user_admin.partner_id + self.customers + self.user_portal.partner_id
        )
