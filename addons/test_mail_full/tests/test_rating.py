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
        record_rating = self.env['mail.test.rating'].browse(self.record_rating.ids)
        self.assertFalse(record_rating.rating_ids)
        self.assertEqual(record_rating.message_partner_ids, self.partner_admin)
        self.assertEqual(len(record_rating.message_ids), 1)

    @users('employee')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_rating_prepare(self):
        record_rating = self.env['mail.test.rating'].browse(self.record_rating.ids)

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
        record_rating = self.env['mail.test.rating'].browse(self.record_rating.ids)
        record_messages = record_rating.message_ids

        # prepare rating token
        access_token = record_rating._rating_get_access_token()

        # apply a rate as note (first click)
        with self.mock_mail_gateway(mail_unlink_sent=False), self.mock_mail_app():
            record_rating.rating_apply(5, token=access_token, feedback='Top Feedback', subtype_xmlid='mail.mt_note')
        message = record_rating.message_ids[0]
        rating = record_rating.rating_ids

        # check posted message
        self.assertEqual(record_rating.message_ids, record_messages + message)
        self.assertIn('Top Feedback', message.body)
        self.assertIn('/rating/static/src/img/rating_5.png', message.body)
        self.assertEqual(message.author_id, self.partner_1)
        self.assertEqual(message.rating_ids, rating)
        self.assertFalse(message.notified_partner_ids)
        self.assertEqual(message.subtype_id, self.env.ref('mail.mt_note'))

        # check rating update
        self.assertTrue(rating.consumed)
        self.assertEqual(rating.feedback, 'Top Feedback')
        self.assertEqual(rating.message_id, message)
        self.assertEqual(rating.rating, 5)
        self.assertEqual(record_rating.rating_last_value, 5)

        # apply a rate again (second click with feedback)
        with self.mock_mail_gateway(mail_unlink_sent=False), self.mock_mail_app():
            record_rating.rating_apply(1, token=access_token, feedback='Bad Feedback')

        # check posted message: a new message is posted with default subtype
        update_message = record_rating.message_ids[0]
        self.assertNotEqual(update_message, message)
        self.assertEqual(record_rating.message_ids, record_messages + message + update_message)
        self.assertIn('Bad Feedback', update_message.body)
        self.assertIn('/rating/static/src/img/rating_1.png', update_message.body)
        self.assertEqual(update_message.author_id, self.partner_1)
        self.assertEqual(update_message.rating_ids, rating)
        self.assertEqual(update_message.notified_partner_ids, self.partner_admin)
        self.assertEqual(update_message.subtype_id, self.env.ref("test_mail_full.mt_mail_test_rating_rating_done"))

        # check rating update
        rating = record_rating.rating_ids
        self.assertTrue(rating.consumed)
        self.assertEqual(rating.feedback, 'Bad Feedback')
        self.assertEqual(rating.message_id, update_message)
        self.assertEqual(rating.rating, 1)
        self.assertEqual(record_rating.rating_last_value, 1)

    @users('__system__')
    @warmup
    def test_rating_last_value_perfs(self):

        record_rating = self.env['mail.test.rating'].browse(self.record_rating.ids)

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

        RECORD_COUNT = 100
        partners = self.env['res.partner'].create([
            {'name': 'Jean-Luc %s' % (idx), 'email': 'jean-luc-%s@opoo.com' % (idx)} for idx in range(RECORD_COUNT)])
        # 3713 requests if only test_mail_full is installed
        # 4510 runbot community
        # 4910 runbot enterprise
        with self.assertQueryCount(__system__=4910):
            record_ratings = self.env['mail.test.rating'].create([{
                'customer_id': partners[idx].id,
                'name': 'Test Rating',
                'user_id': self.user_admin.id,
            } for idx in range(RECORD_COUNT)])
            for record in record_ratings:
                access_token = record._rating_get_access_token()
                record.rating_apply(1, token=access_token)

            record_ratings.rating_ids.write_date = datetime(2022, 1, 1, 14, 00)
            for record in record_ratings:
                access_token = record._rating_get_access_token()
                record.rating_apply(5, token=access_token)

        new_ratings = record_ratings.rating_ids.filtered(lambda r: r.rating == 1)
        new_ratings.write_date = datetime(2022, 2, 1, 14, 00)
        new_ratings.flush_model(['write_date'])
        with self.assertQueryCount(__system__=1):
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
