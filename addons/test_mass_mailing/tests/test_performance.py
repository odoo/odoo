# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail.tests.common import mail_new_test_user
from odoo.tests.common import TransactionCase, users, warmup
from odoo.tests import tagged
from odoo.tools import mute_logger


class TestMassMailPerformanceBase(TransactionCase):

    def setUp(self):
        super(TestMassMailPerformanceBase, self).setUp()

        self.user_employee = mail_new_test_user(
            self.env, login='emp',
            groups='base.group_user',
            name='Ernest Employee', notification_type='inbox')

        self.user_marketing = mail_new_test_user(
            self.env, login='marketing',
            groups='base.group_user,mass_mailing.group_mass_mailing_user',
            name='Martial Marketing', signature='--\nMartial')

        # patch registry to simulate a ready environment
        self.patch(self.env.registry, 'ready', True)


@tagged('mail_performance')
class TestMassMailPerformance(TestMassMailPerformanceBase):

    def setUp(self):
        super(TestMassMailPerformance, self).setUp()
        values = [{
            'name': 'Recipient %s' % x,
            'email_from': 'Recipient <rec.%s@example.com>' % x,
        } for x in range(0, 50)]
        self.mm_recs = self.env['mass.mail.test'].create(values)

    @users('__system__', 'marketing')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_send_mailing(self):
        mailing = self.env['mailing.mailing'].create({
            'name': 'Test',
            'subject': 'Test',
            'body_html': '<p>Hello <a role="button" href="https://www.example.com/foo/bar?baz=qux">quux</a><a role="button" href="/unsubscribe_from_list">Unsubscribe</a></p>',
            'reply_to_mode': 'email',
            'mailing_model_id': self.ref('test_mass_mailing.model_mass_mail_test'),
            'mailing_domain': [('id', 'in', self.mm_recs.ids)],
        })

        with self.assertQueryCount(__system__=2478, marketing=3128):
            mailing.action_send_mail()

        self.assertEqual(mailing.sent, 50)
        self.assertEqual(mailing.delivered, 50)


@tagged('mail_performance')
class TestMassMailBlPerformance(TestMassMailPerformanceBase):

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
        self.env['mass.mail.test.bl'].flush()

    @users('__system__', 'marketing')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_send_mailing_w_bl(self):
        mailing = self.env['mailing.mailing'].create({
            'name': 'Test',
            'subject': 'Test',
            'body_html': '<p>Hello <a role="button" href="https://www.example.com/foo/bar?baz=qux">quux</a><a role="button" href="/unsubscribe_from_list">Unsubscribe</a></p>',
            'reply_to_mode': 'email',
            'mailing_model_id': self.ref('test_mass_mailing.model_mass_mail_test_bl'),
            'mailing_domain': [('id', 'in', self.mm_recs.ids)],
        })

        with self.assertQueryCount(__system__=2865, marketing=3611):
            mailing.action_send_mail()

        self.assertEqual(mailing.sent, 50)
        self.assertEqual(mailing.delivered, 50)
