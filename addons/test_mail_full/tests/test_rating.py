# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail_full.tests.common import TestMailFullCommon, TestMailFullRecipients
from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import mute_logger


@tagged('rating')
class TestRatingFlow(TestMailFullCommon, TestMailFullRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestRatingFlow, cls).setUpClass()

        cls.record_rating = cls.env['mail.test.rating'].create({
            'customer_id': cls.partner_1.id,
            'name': 'Test Rating',
            'user_id': cls.user_admin.id,
        })

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
        access_token = record_rating.rating_get_access_token()
        record_rating.invalidate_cache(fnames=['rating_ids'])

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
        access_token = record_rating.rating_get_access_token()
        record_rating.invalidate_cache(fnames=['rating_ids'])

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
