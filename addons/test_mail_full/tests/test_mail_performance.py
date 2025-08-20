# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from markupsafe import Markup

from odoo import Command
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.test_mail.tests.test_performance import BaseMailPerformance
from odoo.tests.common import users, warmup
from odoo.tests import tagged
from odoo.tools import mute_logger
from odoo.tools.mimetypes import magic
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

        with self.assertQueryCount(employee=91):  # test_mail_full: 80
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
        cls.link_previews = cls.env["mail.link.preview"].create(
            [
                {"source_url": "https://www.odoo.com"},
                {"source_url": "https://www.example.com"},
            ]
        )
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
                "message_link_preview_ids": [
                    Command.create({"link_preview_id": cls.link_previews[0].id}),
                    Command.create({"link_preview_id": cls.link_previews[1].id}),
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

        with self.assertQueryCount(employee=15):
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
                        'raw_access_token': limited_field_access_token(
                            message.attachment_ids[0], 'raw'
                        ),
                        'res_id': record.id,
                        'res_model': record._name,
                    }, {
                        'access_token': message.attachment_ids[1].access_token,
                        'checksum': message.attachment_ids[1].checksum,
                        'filename': 'Test file 0',
                        'id': message.attachment_ids[1].id,
                        'mimetype': expected_mimetype,
                        'name': 'Test file 0',
                        'raw_access_token': limited_field_access_token(
                            message.attachment_ids[1], 'raw'
                        ),
                        'res_id': record.id,
                        'res_model': record._name,
                    }
                ]
            )
            self.assertEqual(format_res["author"]["id"], record.customer_id.id)
            self.assertEqual(format_res["author"]["name"], record.customer_id.display_name)
            self.assertEqual(format_res['author_avatar_url'], f'/web/image/mail.message/{message.id}/author_avatar/50x50')
            self.assertEqual(format_res['date'], datetime(2023, 5, 15, 10, 30, 5))
            self.assertEqual(' '.join(format_res['published_date_str'].split()), '05/15/2023 10:30:05')
            self.assertEqual(format_res['id'], message.id)
            self.assertFalse(format_res['is_internal'])
            self.assertFalse(format_res['is_message_subtype_note'])
            self.assertEqual(format_res['subtype_id'], (comment_subtype.id, comment_subtype.name))
            # should not be in, not asked
            self.assertNotIn('rating_id', format_res)
            self.assertNotIn('rating_stats', format_res)
            self.assertNotIn('rating_value', format_res)

    @mute_logger('odoo.tests', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    @users('employee')
    @warmup
    def test_portal_message_format_rating(self):
        messages_all = self.messages_all.with_user(self.env.user)

        with self.assertQueryCount(employee=29):  # sometimes +1
            res = messages_all.portal_message_format(options={'rating_include': True})

        self.assertEqual(len(res), len(messages_all))
        for format_res, _message, _record in zip(res, messages_all, self.messages_records):
            self.assertEqual(format_res['rating_id']['publisher_avatar'], f'/web/image/res.partner/{self.partner_admin.id}/avatar_128/50x50')
            self.assertEqual(format_res['rating_id']['publisher_comment'], 'Comment')
            self.assertEqual(format_res['rating_id']['publisher_id'], self.partner_admin.id)
            self.assertEqual(" ".join(format_res['rating_id']['publisher_datetime'].split()), '05/13/2023 10:30:05')
            self.assertEqual(format_res['rating_id']['publisher_name'], self.partner_admin.display_name)
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

        with self.assertQueryCount(employee=20):  # randomness: 19+1
            res = message.portal_message_format(options={'rating_include': True})

        self.assertEqual(len(res), 1)


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
