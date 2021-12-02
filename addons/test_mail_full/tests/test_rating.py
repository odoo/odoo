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

        # check posted message: old message is updated
        update_message = record_rating.message_ids[0]
        self.assertEqual(update_message, message)
        self.assertEqual(record_rating.message_ids, record_messages + message)
        self.assertIn('Bad Feedback', message.body)
        self.assertIn('/rating/static/src/img/rating_1.png', message.body)
        self.assertEqual(message.author_id, self.partner_1)
        self.assertEqual(message.rating_ids, rating)
        self.assertEqual(message.notified_partner_ids, self.partner_admin)
        self.assertEqual(message.subtype_id, self.env.ref('mail.mt_comment'))

        # check rating update
        rating = record_rating.rating_ids
        self.assertTrue(rating.consumed)
        self.assertEqual(rating.feedback, 'Bad Feedback')
        self.assertEqual(rating.message_id, message)
        self.assertEqual(rating.rating, 1)

        # customer uses the same email to rate again
        with self.mock_mail_gateway(mail_unlink_sent=False), self.mock_mail_app():
            record_rating.rating_apply(3, token=access_token, feedback='Using old token for feedback')

        # check posted message: new message as old one was notified
        new_message = record_rating.message_ids[0]
        self.assertEqual(record_rating.message_ids, record_messages + message + new_message)
        self.assertIn('Using old token for feedback', new_message.body)
        self.assertIn('/rating/static/src/img/rating_3.png', new_message.body)
        self.assertEqual(new_message.author_id, self.partner_1)
        self.assertEqual(new_message.rating_ids, rating)
        self.assertEqual(new_message.notified_partner_ids, self.partner_admin)
        self.assertEqual(new_message.subtype_id, self.env.ref('mail.mt_comment'))

        # check rating update: same one is used
        rating = record_rating.rating_ids
        self.assertTrue(rating.consumed)
        self.assertEqual(rating.feedback, 'Using old token for feedback')
        self.assertEqual(rating.message_id, new_message)
        self.assertEqual(rating.rating, 3)
