# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.addons.mail.tests.common import  MailCommon
from odoo.tests import tagged
from odoo.tools import formataddr

@tagged('post_install', '-at_install')
class TestMail(MailCommon):

    def test_website_publish_notification(self):
        """ Test that the published/unpublished notifications are sent when publishing/unpublishing an event"""
        published_subtype = self.env.ref('website_event.mt_event_published')
        unpublished_subtype = self.env.ref('website_event.mt_event_unpublished')
        event = self.env['event.event'].create({
            'name': 'Event',
            'date_begin': datetime.today() - timedelta(days=1),
            'date_end': datetime.today() + timedelta(days=1),
        })
        self.flush_tracking()

        follower = self.user_employee.partner_id
        event.message_subscribe(partner_ids=follower.ids, subtype_ids=[published_subtype.id, unpublished_subtype.id])

        event.website_published = True
        self.flush_tracking()

        event.website_published = False
        self.flush_tracking()

        unpublished_message, published_message, creation_message = event.message_ids

        self.assertEqual(unpublished_message.subtype_id, unpublished_subtype)
        self.assertEqual(published_message.subtype_id, published_subtype)
        self.assertEqual(creation_message.subtype_id, self.env.ref('mail.mt_note'))

    def test_registration_mail_url_multi_company_multi_website(self):
        """Check registration confirmation email URL matches the website of the event."""
        company_1 = self.env.company
        company_2 = self.company_2
        self.assertNotEqual(company_1, company_2)

        website_1 = self.env['website'].create({
            'name': 'Website Company 1',
            'company_id': company_1.id,
            'domain': 'http://localhost:8069',
        })
        website_2 = self.env['website'].create({
            'name': 'Website Company 2',
            'company_id': company_2.id,
            'domain': 'http://127.0.0.1:8069',
        })
        self.env['ir.config_parameter'].sudo().set_param('web.base.url', website_1.domain)

        subscription_template = self.env.ref('event.event_subscription')
        mail_scheduler_vals = {
            'interval_unit': 'now',
            'interval_type': 'after_sub',
            'notification_type': 'mail',
            'template_ref': f'mail.template,{subscription_template.id}',
        }
        event_1, event_2 = self.env['event.event'].create([
            {
                'name': 'Event 1',
                'date_begin': datetime(2027, 1, 1, 8, 0),
                'date_end': datetime(2027, 1, 1, 18, 0),
                'company_id': company_1.id,
                'website_id': website_1.id,
                'event_mail_ids': [(0, 0, mail_scheduler_vals)],
            },
            {
                'name': 'Event 2',
                'date_begin': datetime(2027, 1, 1, 8, 0),
                'date_end': datetime(2027, 1, 1, 18, 0),
                'company_id': company_2.id,
                'website_id': website_2.id,
                'event_mail_ids': [(0, 0, mail_scheduler_vals)],
            },
        ])

        customer_1, customer_2 = self.env['res.partner'].create([
            {'name': 'Customer 1', 'email': 'customer1@test.com'},
            {'name': 'Customer 2', 'email': 'customer2@test.com'},
        ])

        with self.mock_mail_gateway():
            self.env['event.registration'].create([
                {
                    'event_id': event_1.id,
                    'name': customer_1.name,
                    'email': customer_1.email,
                    'state': 'open',
                },
                {
                    'event_id': event_2.id,
                    'name': customer_2.name,
                    'email': customer_2.email,
                    'state': 'open',
                },
            ])

        mail_1 = self.assertMailMailWEmails(
            [formataddr((customer_1.name, customer_1.email))], 'outgoing')
        self.assertIn('localhost:8069/', mail_1.body_html)
        self.assertNotIn('127.0.0.1:8069/', mail_1.body_html)

        mail_2 = self.assertMailMailWEmails(
            [formataddr((customer_2.name, customer_2.email))], 'outgoing')
        self.assertIn('127.0.0.1:8069/', mail_2.body_html)
        self.assertNotIn('localhost:8069/', mail_2.body_html)
