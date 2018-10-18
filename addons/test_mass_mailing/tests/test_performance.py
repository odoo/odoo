# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mass_mailing.tests import common
from odoo.tests.common import users, warmup
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('mail_performance')
class TestMassMailPerformance(common.MassMailingCase):

    def setUp(self):
        super(TestMassMailPerformance, self).setUp()
        values = [{
            'name': 'Recipient %s' % x,
            'email_from': 'Recipient <rec.%s@example.com>' % x,
        } for x in range(0, 50)]
        self.mm_recs = self.env['mass.mail.test'].create(values)

    @users('__system__', 'marketing')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_send_mailing(self):
        mailing = self.env['mail.mass_mailing'].create({
            'name': 'Test',
            'body_html': '<p>Hello <a role="button" href="https://www.example.com/foo/bar?baz=qux">quux</a><a role="button" href="/unsubscribe_from_list">Unsubscribe</a></p>',
            'reply_to_mode': 'email',
            'mailing_model_id': self.ref('test_mass_mailing.model_mass_mail_test'),
            'mailing_domain': [('id', 'in', self.mm_recs.ids)],
        })

        with self.assertQueryCount(__system__=2382, marketing=3038):
            mailing.send_mail()

        self.assertEqual(mailing.sent, 50)
        self.assertEqual(mailing.delivered, 50)


@tagged('mail_performance')
class TestMassMailBlPerformance(common.MassMailingCase):

    def setUp(self):
        """ In this setup we prepare 20 blacklist entries. We therefore add
        20 recipients compared to first test in order to have comparable results. """
        super(TestMassMailBlPerformance, self).setUp()
        values = [{
            'name': 'Recipient %s' % x,
            'email_from': 'Recipient <rec.%s@example.com>' % x,
        } for x in range(0, 62)]
        self.mm_recs = self.env['mass.mail.test.bl'].create(values)

        for x in range(1, 13):
            self.env['mail.blacklist'].create({
                'email': 'rec.%s@example.com' % (x * 5)
            })

    @users('__system__', 'marketing')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_send_mailing_w_bl(self):
        mailing = self.env['mail.mass_mailing'].create({
            'name': 'Test',
            'body_html': '<p>Hello <a role="button" href="https://www.example.com/foo/bar?baz=qux">quux</a><a role="button" href="/unsubscribe_from_list">Unsubscribe</a></p>',
            'reply_to_mode': 'email',
            'mailing_model_id': self.ref('test_mass_mailing.model_mass_mail_test_bl'),
            'mailing_domain': [('id', 'in', self.mm_recs.ids)],
        })

        with self.assertQueryCount(__system__=2757, marketing=3509):
            mailing.send_mail()

        self.assertEqual(mailing.sent, 50)
        self.assertEqual(mailing.delivered, 50)
