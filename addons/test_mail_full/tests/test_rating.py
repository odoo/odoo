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

        # prepare rating token
        access_token = record_rating.rating_get_access_token()
        record_rating.invalidate_cache(fnames=['rating_ids'])

        # apply a rate
        with self.mock_mail_gateway(mail_unlink_sent=False), self.mock_mail_app():
            record_rating.rating_apply(5, token=access_token, feedback='Top Feedback')
        message = record_rating.message_ids[0]
        rating = record_rating.rating_ids

        # check posted message
        self.assertIn('Top Feedback', message.body)
        self.assertIn('rating/static/src/img/rating_5.png', message.body)
        self.assertEqual(message.author_id, self.partner_1)
        self.assertFalse(message.rating_ids)
        self.assertEqual(message.notified_partner_ids, self.partner_admin)
        self.assertEqual(message.subtype_id, self.env.ref('mail.mt_comment'))

        # check rating update
        self.assertTrue(rating.consumed)
        self.assertEqual(rating.feedback, 'Top Feedback')
        self.assertFalse(rating.message_id)
        self.assertEqual(rating.rating, 5)
