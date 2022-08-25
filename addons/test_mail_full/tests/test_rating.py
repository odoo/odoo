# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.addons.test_mail_full.tests.common import TestMailFullCommon
from odoo.addons.test_mail_sms.tests.common import TestSMSRecipients
from odoo.tests import tagged
from odoo.tests.common import HttpCase, users, warmup
from odoo.tools import mute_logger


class TestRatingCommon(TestMailFullCommon, TestSMSRecipients):
    @classmethod
    def setUpClass(cls):
        super(TestRatingCommon, cls).setUpClass()

        cls.record_rating = cls.env['mail.test.rating'].create({
            'customer_id': cls.partner_1.id,
            'name': 'Test Rating',
            'user_id': cls.user_admin.id,
        })


@tagged('rating')
class TestRatingFlow(TestRatingCommon):

    def test_initial_values(self):
        record_rating = self.record_rating.with_env(self.env)
        self.assertFalse(record_rating.rating_ids)
        self.assertEqual(record_rating.message_partner_ids, self.partner_admin)
        self.assertEqual(len(record_rating.message_ids), 1)

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_rating_prepare(self):
        record_rating = self.record_rating.with_env(self.env)

        # prepare rating token
        access_token = record_rating._rating_get_access_token()

        # check rating creation
        rating = record_rating.rating_ids
        self.assertEqual(rating.access_token, access_token)
        self.assertFalse(rating.consumed)
        self.assertFalse(rating.is_internal)
        self.assertEqual(rating.partner_id, self.partner_1)
        self.assertEqual(rating.rated_partner_id, self.user_admin.partner_id)
        self.assertFalse(rating.rating)

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_rating_rating_apply(self):
        record_rating = self.record_rating.with_env(self.env)
        record_messages = record_rating.message_ids

        # prepare rating token
        access_token = record_rating._rating_get_access_token()

        # simulate an email click: notification should be delayed
        with self.mock_mail_gateway(mail_unlink_sent=False), self.mock_mail_app():
            record_rating.rating_apply(5, token=access_token, feedback='Top Feedback', notify_delay_send=True)
        message = record_rating.message_ids[0]
        rating = record_rating.rating_ids

        # check posted message
        self.assertEqual(record_rating.message_ids, record_messages + message)
        self.assertIn('Top Feedback', message.body)
        self.assertIn('/rating/static/src/img/rating_5.png', message.body)
        self.assertEqual(message.author_id, self.partner_1)
        self.assertEqual(message.rating_ids, rating)
        self.assertFalse(message.notified_partner_ids)
        self.assertEqual(message.subtype_id, self.env.ref('test_mail_full.mt_mail_test_rating_rating_done'))

        # check rating update
        self.assertTrue(rating.consumed)
        self.assertEqual(rating.feedback, 'Top Feedback')
        self.assertEqual(rating.message_id, message)
        self.assertEqual(rating.rating, 5)
        self.assertEqual(record_rating.rating_last_value, 5)

        # give a feedback: send notifications (notify_delay_send set to False)
        with self.mock_mail_gateway(mail_unlink_sent=False), self.mock_mail_app():
            record_rating.rating_apply(1, token=access_token, feedback='Bad Feedback')

        # check posted message: message is updated
        update_message = record_rating.message_ids[0]
        self.assertEqual(update_message, message, 'Should update first message')
        self.assertEqual(record_rating.message_ids, record_messages + update_message)
        self.assertIn('Bad Feedback', update_message.body)
        self.assertIn('/rating/static/src/img/rating_1.png', update_message.body)
        self.assertEqual(update_message.author_id, self.partner_1)
        self.assertEqual(update_message.rating_ids, rating)
        self.assertEqual(update_message.notified_partner_ids, self.partner_admin)
        self.assertEqual(update_message.subtype_id, self.env.ref("test_mail_full.mt_mail_test_rating_rating_done"))

        # check rating update
        new_rating = record_rating.rating_ids
        self.assertEqual(new_rating, rating, 'Should update first rating')
        self.assertTrue(new_rating.consumed)
        self.assertEqual(new_rating.feedback, 'Bad Feedback')
        self.assertEqual(new_rating.message_id, update_message)
        self.assertEqual(new_rating.rating, 1)
        self.assertEqual(record_rating.rating_last_value, 1)


@tagged('rating')
class TestRatingMixin(TestRatingCommon):

    @users('employee')
    @warmup
    def test_rating_values(self):
        record_rating = self.record_rating.with_env(self.env)

        # prepare rating token
        access_0 = record_rating._rating_get_access_token()
        last_rating = record_rating.rating_apply(3, token=access_0, feedback="This record is meh but it's cheap.")
        # Make sure to update the write_date which is used to retrieve the last rating
        last_rating.write_date = datetime(2022, 1, 1, 14, 00)
        access_1 = record_rating._rating_get_access_token()
        last_rating = record_rating.rating_apply(1, token=access_1, feedback="This record sucks so much. I want to speak to the manager !")
        last_rating.write_date = datetime(2022, 2, 1, 14, 00)
        access_2 = record_rating._rating_get_access_token()
        last_rating = record_rating.rating_apply(5, token=access_2, feedback="This is the best record ever ! I wish I read the documentation before complaining !")
        last_rating.write_date = datetime(2022, 3, 1, 14, 00)
        record_rating.rating_ids.flush_model(['write_date'])

        self.assertEqual(record_rating.rating_last_value, 5, "The last rating is kept.")
        self.assertEqual(record_rating.rating_avg, 3, "The average should be equal to 3")


@tagged('rating', 'mail_performance', 'post_install', '-at_install')
class TestRatingPerformance(TestRatingCommon):

    @users('employee')
    @warmup
    def test_rating_last_value_perfs(self):
        RECORD_COUNT = 100
        partners = self.env['res.partner'].sudo().create([
            {'name': 'Jean-Luc %s' % (idx), 'email': 'jean-luc-%s@opoo.com' % (idx)} for idx in range(RECORD_COUNT)])

        with self.assertQueryCount(employee=1516):  # tmf 1516 / com 5510
            record_ratings = self.env['mail.test.rating'].create([{
                'customer_id': partners[idx].id,
                'name': 'Test Rating',
                'user_id': self.user_admin.id,
            } for idx in range(RECORD_COUNT)])
            self.flush_tracking()

        with self.assertQueryCount(employee=2604):  # tmf 2204 / com 2404
            for record in record_ratings:
                access_token = record._rating_get_access_token()
                record.rating_apply(1, token=access_token)
            self.flush_tracking()

        with self.assertQueryCount(employee=2603):  # tmf 2203 / com 2403
            for record in record_ratings:
                access_token = record._rating_get_access_token()
                record.rating_apply(5, token=access_token)
            self.flush_tracking()

        with self.assertQueryCount(employee=1):
            record_ratings._compute_rating_last_value()
            vals = [val == 5 for val in record_ratings.mapped('rating_last_value')]
            self.assertTrue(all(vals), "The last rating is kept.")


@tagged('rating')
class TestRatingRoutes(HttpCase, TestRatingCommon):

    def test_open_rating_route(self):
        access_token = self.record_rating._rating_get_access_token()
        self.url_open(f"/rate/{access_token}/5")

        rating = self.record_rating.rating_ids
        self.assertTrue(rating.consumed)
        self.assertEqual(rating.rating, 5)
        self.assertEqual(self.record_rating.rating_last_value, 5)
