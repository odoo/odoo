# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from markupsafe import Markup

from odoo import fields
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.test_mail.tests.test_performance import BaseMailPerformance
from odoo.tests.common import HttpCase, users, warmup
from odoo.tests import tagged
from odoo.tools import mute_logger
from odoo.tools.misc import limited_field_access_token


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

        with self.assertQueryCount(employee=88):  # test_mail_full: 87
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
class TestPortalFormatPerformance(FullBaseMailPerformance, HttpCase):
    """Test the performance of the portal messages format. The messages may not make sense
    functionally, but they are designed to cover as much of the code as possible in terms of
    number of queries.
    The message with the subtype note is created to emphasize that messages with this subtype
    are not fetched in the portal."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.record = cls.env['mail.test.rating'].create([
            {
                'customer_id': cls.customers[0].id,
                'name': 'TestRating',
                'user_id': cls.test_users[0].id,

            }
        ])
        cls.comment_1 = cls.env['mail.message'].create([
            {
                'attachment_ids': [
                    (0, 0, {
                        'datas': 'data',
                        'name': 'Test file',
                        'res_id': cls.record.id,
                        'res_model': cls.record._name,
                    })
                ],
                'author_id': cls.record.customer_id.id,
                'body': '<p>Comment 1</p>',
                'date': datetime(2023, 5, 15, 10, 30, 5),
                'email_from': cls.record.customer_id.email_formatted,
                'link_preview_ids': [(0, 0, {'source_url': 'https://www.odoo.com'})],
                'notification_ids': [
                    (0, 0, {
                        'is_read': False,
                        'notification_type': 'inbox',
                        'res_partner_id': cls.customers[0].id,
                    })
                ],
                'message_type': 'comment',
                'model': cls.record._name,
                'partner_ids': [(4, cls.customers[0].id), (4, cls.customers[1].id)],
                'reaction_ids': [
                    (0, 0, {
                        'content': '😊',
                        'partner_id': cls.customers[0].id
                    }), (0, 0, {
                        'content': '👍',
                        'partner_id': cls.customers[1].id
                    }),
                ],
                'res_id': cls.record.id,
                'subject': 'Test Rating',
                'subtype_id': cls.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment'),
                'starred_partner_ids': [
                    (4, cls.customers[0].id),
                    (4, cls.customers[1].id),
                ],
                'tracking_value_ids': [
                    (0, 0, {
                        'field_id': cls.env['ir.model.fields']._get(cls.record._name, 'user_id').id,
                        'new_value_char': 'new 1',
                        'new_value_integer': cls.record.user_id.id,
                        'old_value_char': 'old 1',
                        'old_value_integer': cls.user_admin.id,
                    }),
                ]
            }
        ])
        cls.comment_2 = cls.env["mail.message"].create([
            {
                "body": "Comment 2",
                'message_type': 'comment',
                'model': cls.record._name,
                "res_id": cls.record.id,
                "subtype_id": cls.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment'),
            }
        ])
        cls.note = cls.env["mail.message"].create([
            {
                "body": "Note",
                'message_type': 'comment',
                'model': cls.record._name,
                "res_id": cls.record.id,
                "subtype_id": cls.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
            }
        ])

        cls.rating = cls.env['rating.rating'].create([
            {
                'consumed': True,
                'message_id': cls.comment_1.id,
                'partner_id': cls.record.customer_id.id,
                'publisher_comment': 'Comment',
                'publisher_id': cls.user_admin.partner_id.id,
                'publisher_datetime': datetime(2023, 5, 15, 10, 30, 5) - timedelta(days=2),
                'rated_partner_id': cls.record.user_id.partner_id.id,
                'rating': 4,
                'res_id': cls.comment_1.res_id,
                'res_model_id': cls.env['ir.model']._get_id(cls.comment_1.model),
            }
        ])

    @mute_logger("odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink")
    @users("employee")
    @warmup
    def test_portal_message_format(self):
        self.authenticate(self.user_employee.login, self.user_employee.login)
        messages_count = self.env["mail.message"].search_count(
            [("res_id", "=", self.record.id), ("model", "=", self.record._name)]
        )
        with self.assertQueryCount(employee=34):
            res = self.make_jsonrpc_request(
                route="/mail/thread/messages",
                params={
                    "thread_model": self.record._name,
                    "thread_id": self.record.id,
                    "fetch_portal_message": True,
                },
            )
        self.assertNotEqual(len(res["messages"]), messages_count)
        expected_data = {
            "data": {
                "MessageReactions": [
                    {
                        "content": "👍",
                        "count": 1,
                        "message": self.comment_1.id,
                        "personas": [{"id": self.customers[1].id, "type": "partner"}],
                        "sequence": min(
                            self.comment_1.reaction_ids.filtered(lambda r: r.content == "👍").ids
                        ),
                    },
                    {
                        "content": "😊",
                        "count": 1,
                        "message": self.comment_1.id,
                        "personas": [{"id": self.customers[0].id, "type": "partner"}],
                        "sequence": min(
                            self.comment_1.reaction_ids.filtered(lambda r: r.content == "😊").ids
                        ),
                    },
                ],
                "ir.attachment": [
                    {
                        "checksum": "8f06741ba6002d0e0df1118d1f32472205fa8fe2",
                        "create_date": fields.Datetime.to_string(
                            self.comment_1.attachment_ids.create_date
                        ),
                        "id": self.comment_1.attachment_ids.id,
                        "mimetype": "application/octet-stream",
                        "name": "Test file",
                        "res_name": "TestRating",
                        "thread": {"id": self.record.id, "model": self.record._name},
                        "type": "binary",
                        "url": False,
                        "voice": False,
                    }
                ],
                "mail.link.preview": [
                    {
                        "id": self.comment_1.link_preview_ids.id,
                        "image_mimetype": False,
                        "message_id": self.comment_1.id,
                        "og_description": False,
                        "og_image": False,
                        "og_mimetype": False,
                        "og_site_name": False,
                        "og_title": False,
                        "og_type": False,
                        "source_url": "https://www.odoo.com",
                    },
                ],
                "mail.message": [
                    {
                        "attachment_ids": [],
                        "author": {"id": self.comment_2.author_id.id, "type": "partner"},
                        "body": "<p>Comment 2</p>",
                        "create_date": fields.Datetime.to_string(self.comment_2.create_date),
                        "date": fields.Datetime.to_string(self.comment_2.date),
                        "default_subject": "TestRating",
                        "email_from": '"OdooBot" <odoobot@example.com>',
                        "id": self.comment_2.id,
                        "incoming_email_cc": False,
                        "incoming_email_to": False,
                        "is_discussion": True,
                        "is_note": False,
                        "link_preview_ids": [],
                        "message_type": "comment",
                        "model": self.record._name,
                        "needaction": False,
                        "notification_ids": [],
                        "pinned_at": False,
                        "rating_id": False,
                        "reactions": [],
                        "recipients": [],
                        "record_name": "TestRating",
                        "res_id": self.record.id,
                        "scheduledDatetime": False,
                        "starred": False,
                        "subject": False,
                        "subtype_description": False,
                        "thread": {"id": self.record.id, "model": self.record._name},
                        "trackingValues": [],
                        "write_date": fields.Datetime.to_string(self.comment_2.write_date),
                    },
                    {
                        "attachment_ids": [self.comment_1.attachment_ids.id],
                        "author": {"id": self.comment_1.author_id.id, "type": "partner"},
                        "body": "<p>Comment 1</p>",
                        "create_date": fields.Datetime.to_string(self.comment_1.create_date),
                        "date": fields.Datetime.to_string(self.comment_1.date),
                        "default_subject": "TestRating",
                        "email_from": '"Test Full Customer 0" <customer.full.test.0@example.com>',
                        "id": self.comment_1.id,
                        "incoming_email_cc": False,
                        "incoming_email_to": False,
                        "is_discussion": True,
                        "is_note": False,
                        "link_preview_ids": self.comment_1.link_preview_ids.ids,
                        "message_type": "comment",
                        "model": self.record._name,
                        "needaction": False,
                        "notification_ids": self.comment_1.notification_ids.ids,
                        "pinned_at": False,
                        "rating_id": self.rating.id,
                        "reactions": [
                            {"message": self.comment_1.id, "content": "👍"},
                            {"message": self.comment_1.id, "content": "😊"},
                        ],
                        "recipients": [
                            {"id": self.customers[0].id, "type": "partner"},
                            {"id": self.customers[1].id, "type": "partner"},
                        ],
                        "record_name": "TestRating",
                        "res_id": self.record.id,
                        "scheduledDatetime": False,
                        "starred": False,
                        "subject": "Test Rating",
                        "subtype_description": False,
                        "thread": {"id": self.record.id, "model": self.record._name},
                        "trackingValues": [
                            {
                                "changedField": "Responsible",
                                "id": self.comment_1.tracking_value_ids.id,
                                "fieldName": "user_id",
                                "fieldType": "many2one",
                                "newValue": {"currencyId": False, "value": "new 1"},
                                "oldValue": {"currencyId": False, "value": "old 1"},
                            }
                        ],
                        "write_date": fields.Datetime.to_string(self.comment_1.write_date),
                    },
                ],
                "mail.notification": [
                    {
                        "failure_type": False,
                        "id": self.comment_1.notification_ids.id,
                        "mail_message_id": self.comment_1.id,
                        "notification_status": "ready",
                        "notification_type": "inbox",
                        "persona": {"id": self.customers[0].id, "type": "partner"},
                    }
                ],
                "mail.thread": [
                    {
                        "display_name": "TestRating",
                        "id": self.record.id,
                        "model": self.record._name,
                        "module_icon": "/base/static/description/icon.png",
                        "rating_avg": 4.0,
                        "rating_count": 1,
                    }
                ],
                "rating.rating": [
                    {
                        "id": self.rating.id,
                        "message_id": self.comment_1.id,
                        "publisher_comment": "Comment",
                        "publisher_datetime": fields.Datetime.to_string(self.rating.publisher_datetime),
                        "publisher_id": {"id": self.user_admin.partner_id.id, "type": "partner"},
                        "rating": 4.0,
                        "rating_image_url": "/rating/static/src/img/rating_5.png",
                        "rating_text": "top",
                    }
                ],
                "res.partner": [
                    {
                        "avatar_128_access_token": limited_field_access_token(
                            self.customers[1], "avatar_128"
                        ),
                        "id": self.customers[1].id,
                        "name": "Test Full Customer 1",
                        "write_date": fields.Datetime.to_string(self.customers[1].write_date),
                    },
                    {
                        "avatar_128_access_token": limited_field_access_token(
                            self.customers[0], "avatar_128"
                        ),
                        "email": "customer.full.test.0@example.com",
                        "id": self.customers[0].id,
                        "isInternalUser": False,
                        "is_company": False,
                        "name": "Test Full Customer 0",
                        "userId": False,
                        "write_date": fields.Datetime.to_string(self.customers[0].write_date),
                    },
                    {
                        "id": self.user_admin.partner_id.id,
                        "isInternalUser": True,
                        "is_company": False,
                        "name": "Mitchell Admin",
                        "userId": self.user_admin.id,
                        "write_date": fields.Datetime.to_string(self.user_admin.partner_id.write_date),
                    },
                    {
                        "avatar_128_access_token": limited_field_access_token(
                            self.user_root.partner_id, "avatar_128"
                        ),
                        "id": self.user_root.partner_id.id,
                        "isInternalUser": True,
                        "is_company": False,
                        "name": "OdooBot",
                        "userId": self.user_root.id,
                        "write_date": fields.Datetime.to_string(
                            self.user_root.partner_id.write_date),
                    },
                ],
            },
            "messages": [self.comment_2.id, self.comment_1.id],
        }
        self.assertEqual(res, expected_data)
