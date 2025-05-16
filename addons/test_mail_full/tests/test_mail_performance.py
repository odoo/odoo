# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from markupsafe import Markup

from odoo import Command, fields
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.test_mail.tests.test_performance import BaseMailPerformance
from odoo.tests.common import HttpCase, users, warmup
from odoo.tests import tagged
from odoo.tools import mute_logger


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

        with self.assertQueryCount(employee=89):  # test_mail_full: 80
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
        cls.record = cls.env["mail.test.rating"].create([
            {
                "customer_id": cls.customers[0].id,
                "name": "TestRating",
                "user_id": cls.test_users[0].id,

            }
        ])
        cls.comment_1 = cls.env["mail.message"].create([
            {
                "attachment_ids": [
                    (0, 0, {
                        "datas": "data",
                        "name": "Test file",
                        "res_id": cls.record.id,
                        "res_model": cls.record._name,
                    })
                ],
                "author_id": cls.record.customer_id.id,
                "body": "<p>Comment 1</p>",
                "date": datetime(2023, 5, 15, 10, 30, 5),
                "email_from": cls.record.customer_id.email_formatted,
                "message_link_preview_ids": [
                    Command.create({"link_preview_id": cls.env["mail.link.preview"].create(
                        [
                            {"source_url": "https://www.odoo.com"},
                        ]
                    ).id}),
                ],
                "notification_ids": [
                    (0, 0, {
                        "is_read": False,
                        "notification_type": "inbox",
                        "res_partner_id": cls.customers[0].id,
                    })
                ],
                "message_type": "comment",
                "model": cls.record._name,
                "partner_ids": [(4, cls.customers[0].id), (4, cls.customers[1].id)],
                "reaction_ids": [
                    (0, 0, {
                        "content": "😊",
                        "partner_id": cls.customers[0].id
                    }), (0, 0, {
                        "content": "👍",
                        "partner_id": cls.customers[1].id
                    }),
                ],
                "res_id": cls.record.id,
                "subject": "Test Rating",
                "subtype_id": cls.env["ir.model.data"]._xmlid_to_res_id("mail.mt_comment"),
                "starred_partner_ids": [
                    (4, cls.customers[0].id),
                    (4, cls.customers[1].id),
                ],
                "tracking_value_ids": [
                    (0, 0, {
                        "field_id": cls.env["ir.model.fields"]._get(cls.record._name, "user_id").id,
                        "new_value_char": "new 1",
                        "new_value_integer": cls.record.user_id.id,
                        "old_value_char": "old 1",
                        "old_value_integer": cls.user_admin.id,
                    }),
                ]
            }
        ])
        cls.comment_2 = cls.env["mail.message"].create([
            {
                "body": "Comment 2",
                "message_type": "comment",
                "model": cls.record._name,
                "res_id": cls.record.id,
                "subtype_id": cls.env["ir.model.data"]._xmlid_to_res_id("mail.mt_comment"),
            }
        ])
        cls.note = cls.env["mail.message"].create([
            {
                "body": "Note",
                "message_type": "comment",
                "model": cls.record._name,
                "res_id": cls.record.id,
                "subtype_id": cls.env["ir.model.data"]._xmlid_to_res_id("mail.mt_note"),
            }
        ])

        cls.rating = cls.env["rating.rating"].create([
            {
                "consumed": True,
                "message_id": cls.comment_1.id,
                "partner_id": cls.record.customer_id.id,
                "publisher_comment": "Comment",
                "publisher_id": cls.user_admin.partner_id.id,
                "publisher_datetime": datetime(2023, 5, 15, 10, 30, 5) - timedelta(days=2),
                "rated_partner_id": cls.record.user_id.partner_id.id,
                "rating": 4,
                "res_id": cls.comment_1.res_id,
                "res_model_id": cls.env["ir.model"]._get_id(cls.comment_1.model),
            }
        ])

    @mute_logger("odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink")
    @users("employee")
    @warmup
    def test_portal_fetch_messages(self):
        self.authenticate(self.user_employee.login, self.user_employee.login)
        with self.assertQueryCount(employee=35):
            res = self.make_jsonrpc_request(
                route="/mail/thread/messages",
                params={
                    "thread_model": self.record._name,
                    "thread_id": self.record.id,
                    "only_portal": True,
                },
            )
        fetched_messages = res["data"]["mail.message"]
        self.assertEqual(len(fetched_messages), 2)  # 2 comments only
        self.assertMessageFields(fetched_messages[0], {"is_note": False})
        self.assertMessageFields(fetched_messages[1], {"is_note": False})
        self.assertEqual(len(res["data"]["rating.rating"]), 1)
        rating = res["data"]["rating.rating"][0]
        self.assertEqual(rating["message_id"], self.comment_1.id)
        self.assertEqual(rating["publisher_comment"], "Comment")
        self.assertEqual(
            rating["publisher_datetime"],
            fields.Datetime.to_string(self.rating.publisher_datetime))
        self.assertEqual(rating["publisher_id"]["id"], self.user_admin.partner_id.id)

    @mute_logger("odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink")
    @users("employee")
    @warmup
    def test_portal_thread_rating_stats(self):
        self.authenticate(self.user_employee.login, self.user_employee.login)
        with self.assertQueryCount(employee=5):
            res = self.make_jsonrpc_request(
                route="/mail/data",
                params={
                    "fetch_params": [
                        [
                            "mail.thread",
                            {
                                "thread_id": self.record.id,
                                "thread_model": self.record._name,
                                "request_list": ["rating_stats"],
                            },
                        ]
                    ]
                },
            )
        self.assertEqual(
            res["mail.thread"][0]["rating_stats"],
            {
                "avg": 4.0,
                "percent": {"1": 0.0, "2": 0.0, "3": 0.0, "4": 100.0, "5": 0.0},
                "total": 1,
            },
        )


@tagged('rating', 'mail_performance', 'post_install', '-at_install')
class TestRatingPerformance(FullBaseMailPerformance):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.RECORD_COUNT = 20

        cls.partners = cls.env['res.partner'].sudo().create([
            {'name': 'Jean-Luc %s' % (idx), 'email': 'jean-luc-%s@opoo.com' % (idx)}
            for idx in range(cls.RECORD_COUNT)])

        # create records with 2 ratings to check batch statistics on them
        responsibles = [cls.user_admin, cls.user_employee, cls.env['res.users']]
        cls.record_ratings = cls.env['mail.test.rating'].create([{
            'customer_id': cls.partners[idx].id,
            'name': f'Test Rating {idx}',
            'user_id': responsibles[idx % 3].id,
        } for idx in range(cls.RECORD_COUNT)])
        rates = [enum % 5 for enum, _rec in enumerate(cls.record_ratings)]
        # create rating from 1 -> 5 for each record
        for rate, record in zip(rates, cls.record_ratings, strict=True):
            record.rating_apply(rate + 1, token=record._rating_get_access_token())
        # create rating with 4 or 5 (half records)
        for record in cls.record_ratings[:10]:
            record.rating_apply(4, token=record._rating_get_access_token())
        for record in cls.record_ratings[10:]:
            record.rating_apply(5, token=record._rating_get_access_token())

    def apply_ratings(self, rate):
        for record in self.record_ratings:
            access_token = record._rating_get_access_token()
            record.rating_apply(rate, token=access_token)
        self.flush_tracking()

    def create_ratings(self, model):
        self.record_ratings = self.env[model].create([{
            'customer_id': self.partners[idx].id,
            'name': 'Test Rating',
            'user_id': self.user_admin.id,
        } for idx in range(self.RECORD_COUNT)])
        self.flush_tracking()

    @users('employee')
    @warmup
    def test_rating_api_rating_get_operator(self):
        user_names = []
        with self.assertQueryCount(employee=4):  # tmf: 4
            ratings = self.record_ratings.with_env(self.env)
            for rating in ratings:
                user_names.append(rating._rating_get_operator().name)
        expected_names = ['Mitchell Admin', 'Ernest Employee', False] * 6 + ['Mitchell Admin', 'Ernest Employee']
        for partner_name, expected_name in zip(user_names, expected_names, strict=True):
            self.assertEqual(partner_name, expected_name)

    @users('employee')
    @warmup
    def test_rating_api_rating_get_partner(self):
        partner_names = []
        with self.assertQueryCount(employee=3):  # tmf: 3
            ratings = self.record_ratings.with_env(self.env)
            for rating in ratings:
                partner_names.append(rating._rating_get_partner().name)
        for partner_name, expected in zip(partner_names, self.partners, strict=True):
            self.assertEqual(partner_name, expected.name)

    @users('employee')
    @warmup
    def test_rating_get_grades_perfs(self):
        with self.assertQueryCount(employee=1):
            ratings = self.record_ratings.with_env(self.env)
            grades = ratings.rating_get_grades()
        self.assertDictEqual(grades, {'great': 28, 'okay': 4, 'bad': 8})

    @users('employee')
    @warmup
    def test_rating_get_stats_perfs(self):
        with self.assertQueryCount(employee=1):
            ratings = self.record_ratings.with_env(self.env)
            stats = ratings.rating_get_stats()
        self.assertDictEqual(stats, {'avg': 3.75, 'total': 40, 'percent': {1: 10.0, 2: 10.0, 3: 10.0, 4: 35.0, 5: 35.0}})

    @users('employee')
    @warmup
    def test_rating_last_value_perfs(self):
        with self.assertQueryCount(employee=233):  # tmf: 233
            self.create_ratings('mail.test.rating.thread')

        with self.assertQueryCount(employee=263):  # tmf: 263
            self.apply_ratings(1)

        with self.assertQueryCount(employee=222):  # tmf: 222
            self.apply_ratings(5)

    @users('employee')
    @warmup
    def test_rating_last_value_perfs_with_rating_mixin(self):
        with self.assertQueryCount(employee=256):  # tmf: 256
            self.create_ratings('mail.test.rating')

        with self.assertQueryCount(employee=285):  # tmf: 285
            self.apply_ratings(1)

        with self.assertQueryCount(employee=264):  # tmf: 264
            self.apply_ratings(5)

        with self.assertQueryCount(employee=1):
            self.record_ratings._compute_rating_last_value()
            vals = (val == 5 for val in self.record_ratings.mapped('rating_last_value'))
            self.assertTrue(all(vals), "The last rating is kept.")

    @users('employee')
    @warmup
    def test_rating_stat_fields(self):
        expected_texts = ['ok', 'ok', 'ok', 'top', 'top'] * 2 + ['ok', 'ok', 'top', 'top', 'top'] * 2
        expected_satis = [50.0, 50.0, 50.0, 100.0, 100.0] * 4
        with self.assertQueryCount(employee=2):
            ratings = self.record_ratings.with_env(self.env)
            for rating, text, satisfaction in zip(ratings, expected_texts, expected_satis, strict=True):
                self.assertEqual(rating.rating_avg_text, text)
                self.assertEqual(rating.rating_percentage_satisfaction, satisfaction)
