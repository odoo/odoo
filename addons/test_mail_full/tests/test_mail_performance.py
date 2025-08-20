# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
from datetime import datetime, timedelta
from markupsafe import Markup

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.test_mail.tests.test_performance import BaseMailPerformance
from odoo.tests.common import users, warmup
from odoo.tests import tagged
from odoo.tools import mute_logger
from odoo.tools.mimetypes import magic


@tagged('mail_performance', 'post_install', '-at_install')
class FullBaseMailPerformance(BaseMailPerformance):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

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
            {
                'country_id': cls.env.ref('base.be').id,
                'email': f'customer.full.test.{idx}@example.com',
                'name': f'Test Full Customer {idx}',
                'mobile': f'045600000{idx}',
                'phone': f'045611111{idx}',
            } for idx in range(5)
        ])
        cls.test_users = cls.user_employee + cls.user_test + cls.user_test_email + cls.user_emp_email + cls.user_portal

        # records
        cls.record_containers = cls.env['mail.test.container.mc'].create([
            {
                'alias_name': 'test-alias-0',
                'customer_id': cls.customers[0].id,
                'name': 'Test Container 1',
            },
            {
                'alias_name': 'test-alias-1',
                'customer_id': cls.customers[1].id,
                'name': 'Test Container 2',
            },
        ])
        cls.record_ticket = cls.env['mail.test.ticket.mc'].create({
            'email_from': 'email.from@test.example.com',
            'container_id': cls.record_containers[0].id,
            'customer_id': False,
            'name': 'Test Ticket',
            'user_id': cls.user_emp_email.id,
        })
        cls.record_ticket.message_subscribe(cls.customers.ids + cls.user_admin.partner_id.ids + cls.user_portal.partner_id.ids)


@tagged('mail_performance', 'post_install', '-at_install')
class TestMailPerformance(FullBaseMailPerformance):

    def test_assert_initial_values(self):
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

        with self.assertQueryCount(employee=101):  # test_mail_full: 100
            new_message = record_ticket.message_post(
                attachment_ids=attachments.ids,
                body=Markup('<p>Test Content</p>'),
                message_type='comment',
                subject='Test Subject',
                subtype_xmlid='mail.mt_comment',
            )

        self.assertEqual(
            new_message.notified_partner_ids,
            self.user_emp_email.partner_id + self.user_admin.partner_id + self.customers + self.user_portal.partner_id
        )


@tagged('mail_performance', 'post_install', '-at_install')
class TestPortalFormatPerformance(FullBaseMailPerformance):
    """Test performance of `portal_message_format` with multiple messages
    with multiple attachments, with ratings.

    Those messages might not make sense functionally but they are crafted to
    cover as much of the code as possible in regard to number of queries.

    Setup :
      * 5 records (self.containers -> 5 mail.test.rating records, with
        a different customer_id each)
      * 2 messages / record
      * 2 attachments / message
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # rating-enabled test records
        cls.record_ratings = cls.env['mail.test.rating'].create([
            {
                'customer_id': cls.customers[idx].id,
                'name': f'TestRating_{idx}',
                'user_id': cls.test_users[idx].id,

            }
            for idx in range(5)
        ])

        # messages and ratings
        user_id_field = cls.env['ir.model.fields']._get(cls.record_ratings._name, 'user_id')
        comment_subtype_id = cls.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment')
        cls.messages_all = cls.env['mail.message'].sudo().create([
            {
                'attachment_ids': [
                    (0, 0, {
                        'datas': 'data',
                        'name': f'Test file {att_idx}',
                        'res_id': record.id,
                        'res_model': record._name,
                    })
                    for att_idx in range(2)
                ],
                'author_id': record.customer_id.id,
                'body': f'<p>Test {msg_idx}</p>',
                'date': datetime(2023, 5, 15, 10, 30, 5),
                'email_from': record.customer_id.email_formatted,
                'link_preview_ids': [
                    (0, 0, {
                        'source_url': 'https://www.odoo.com',
                    }), (0, 0, {
                        'source_url': 'https://www.example.com',
                    }),
                ],
                'notification_ids': [
                    (0, 0, {
                        'is_read': False,
                        'notification_type': 'inbox',
                        'res_partner_id': cls.customers[(msg_idx * 2)].id,
                    }),
                    (0, 0, {
                        'is_read': True,
                        'notification_type': 'email',
                        'notification_status': 'sent',
                        'res_partner_id': cls.customers[(msg_idx * 2) + 1].id,
                    }),
                ],
                'message_type': 'comment',
                'model': record._name,
                'partner_ids': [
                    (4, cls.customers[(msg_idx * 2)].id),
                    (4, cls.customers[record_idx].id),
                ],
                'reaction_ids': [
                    (0, 0, {
                        'content': 'https://www.odoo.com',
                        'partner_id': cls.customers[(msg_idx * 2) + 1].id
                    }), (0, 0, {
                        'content': 'https://www.example.com',
                        'partner_id': cls.customers[record_idx].id
                    }),
                ],
                'res_id': record.id,
                'subject': f'Test Rating {msg_idx}',
                'subtype_id': comment_subtype_id,
                'starred_partner_ids': [
                    (4, cls.customers[(msg_idx * 2)].id),
                    (4, cls.customers[(msg_idx * 2) + 1].id),
                ],
                'tracking_value_ids': [
                    (0, 0, {
                        'field_id': user_id_field.id,
                        'new_value_char': 'new 1',
                        'new_value_integer': record.user_id.id,
                        'old_value_char': 'old 1',
                        'old_value_integer': cls.user_admin.id,
                    }),
                ]
            }
            for msg_idx in range(2)
            for record_idx, record in enumerate(cls.record_ratings)
        ])

        cls.messages_records = [cls.env[message.model].browse(message.res_id) for message in cls.messages_all]
        # ratings values related to rating-enabled records
        cls.ratings_all = cls.env['rating.rating'].sudo().create([
            {
                'consumed': True,
                'message_id': message.id,
                'partner_id': record.customer_id.id,
                'publisher_comment': 'Comment',
                'publisher_id': cls.user_admin.partner_id.id,
                'publisher_datetime': datetime(2023, 5, 15, 10, 30, 5) - timedelta(days=2),
                'rated_partner_id': record.user_id.partner_id.id,
                'rating': 4,
                'res_id': message.res_id,
                'res_model_id': cls.env['ir.model']._get_id(message.model),
            }
            for rating_idx in range(2)
            for message, record in zip(cls.messages_all, cls.messages_records)
        ])

    def test_assert_initial_values(self):
        self.assertEqual(len(self.messages_all), 5 * 2)
        self.assertEqual(len(self.ratings_all), len(self.messages_all) * 2)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('employee')
    @warmup
    def test_portal_message_format_norating(self):
        messages_all = self.messages_all.with_user(self.env.user)

        with self.assertQueryCount(employee=31):
            # res = messages_all.portal_message_format(options=None)
            res = messages_all.portal_message_format(options={'rating_include': False})

        comment_subtype = self.env.ref('mail.mt_comment')
        self.assertEqual(len(res), len(messages_all))
        for format_res, message, record in zip(res, messages_all, self.messages_records):
            self.assertEqual(len(format_res['attachment_ids']), 2)
            expected_mimetype = 'text/plain' if magic else 'application/octet-stream'
            self.assertEqual(
                format_res['attachment_ids'],
                [
                    {
                        'access_token': message.attachment_ids[0].access_token,
                        'checksum': message.attachment_ids[0].checksum,
                        'filename': 'Test file 1',
                        'id': message.attachment_ids[0].id,
                        'mimetype': expected_mimetype,
                        'name': 'Test file 1',
                        'res_id': record.id,
                        'res_model': record._name,
                    }, {
                        'access_token': message.attachment_ids[1].access_token,
                        'checksum': message.attachment_ids[1].checksum,
                        'filename': 'Test file 0',
                        'id': message.attachment_ids[1].id,
                        'mimetype': expected_mimetype,
                        'name': 'Test file 0',
                        'res_id': record.id,
                        'res_model': record._name,
                    }
                ]
            )
            self.assertEqual(format_res['author_id'], (record.customer_id.id, record.customer_id.display_name))
            self.assertEqual(format_res['author_avatar_url'], f'/web/image/mail.message/{message.id}/author_avatar/50x50')
            self.assertEqual(format_res['date'], datetime(2023, 5, 15, 10, 30, 5))
            self.assertEqual(
                re.sub(r'\s+', ' ', format_res['published_date_str']),
                'May 15, 2023, 10:30:05 AM',
            )
            self.assertEqual(format_res['id'], message.id)
            self.assertFalse(format_res['is_internal'])
            self.assertFalse(format_res['is_message_subtype_note'])
            self.assertEqual(format_res['subtype_id'], (comment_subtype.id, comment_subtype.name))
            # should not be in, not asked
            self.assertNotIn('rating', format_res)
            self.assertNotIn('rating_stats', format_res)
            self.assertNotIn('rating_value', format_res)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('employee')
    @warmup
    def test_portal_message_format_rating(self):
        messages_all = self.messages_all.with_user(self.env.user)

        with self.assertQueryCount(employee=45):
            res = messages_all.portal_message_format(options={'rating_include': True})

        self.assertEqual(len(res), len(messages_all))
        for format_res, _message, _record in zip(res, messages_all, self.messages_records):
            self.assertEqual(format_res['rating']['publisher_avatar'], f'/web/image/res.partner/{self.partner_admin.id}/avatar_128/50x50')
            self.assertEqual(format_res['rating']['publisher_comment'], 'Comment')
            self.assertEqual(format_res['rating']['publisher_id'], self.partner_admin.id)
            self.assertEqual(
                re.sub(r'\s+', ' ', format_res['rating']['publisher_datetime']),
                'May 13, 2023, 10:30:05 AM',
            )
            self.assertEqual(format_res['rating']['publisher_name'], self.partner_admin.display_name)
            self.assertDictEqual(
                format_res['rating_stats'],
                {'avg': 4.0, 'total': 4, 'percent': {1: 0.0, 2: 0.0, 3: 0.0, 4: 100.0, 5: 0.0}}
            )
            self.assertEqual(format_res['rating_value'], 4)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('employee')
    @warmup
    def test_portal_message_format_monorecord(self):
        message = self.messages_all[0].with_user(self.env.user)

        with self.assertQueryCount(employee=18):
            res = message.portal_message_format(options={'rating_include': True})

        self.assertEqual(len(res), 1)
