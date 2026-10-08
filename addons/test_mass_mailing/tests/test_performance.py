# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.test_mail.tests.test_performance import BaseMailPerformance
from odoo.tests.common import users, warmup
from odoo.tests import tagged
from odoo.tools import mute_logger


class TestMassMailPerformanceBase(BaseMailPerformance):

    @classmethod
    def setUpClass(cls):
        super(TestMassMailPerformanceBase, cls).setUpClass()

        cls.user_marketing = mail_new_test_user(
            cls.env,
            groups='base.group_user,mass_mailing.group_mass_mailing_user',
            login='marketing',
            name='Martial Marketing',
            signature='--\nMartial'
        )

@tagged('mail_performance', 'post_install', '-at_install')
class TestMassMailPerformance(TestMassMailPerformanceBase):

    def setUp(self):
        super(TestMassMailPerformance, self).setUp()
        values = [{
            'name': 'Recipient %s' % x,
            'email_from': 'Recipient <rec.%s@example.com>' % x,
        } for x in range(0, 50)]
        self.mm_recs = self.env['mailing.performance'].create(values)

    @users('__system__', 'marketing')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_send_mailing(self):
        mailing = self.env['mailing.mailing'].create({
            'name': 'Test',
            'subject': 'Test',
            'body_html': '<p>Hello <a role="button" href="https://www.example.com/foo/bar?baz=qux">quux</a><a role="button" href="/unsubscribe_from_list">Unsubscribe</a></p>',
            'reply_to_mode': 'new',
            'mailing_model_id': self.ref('test_mass_mailing.model_mailing_performance'),
            'mailing_domain': [('id', 'in', self.mm_recs.ids)],
        })

        # runbot needs +101 compared to local
        with self.assertQueryCount(__system__=1280, marketing=1281):  # 1178, 1180
            mailing.action_send_mail()

        self.assertEqual(mailing.sent, 50)
        self.assertEqual(mailing.delivered, 50)

        mails = self.env['mail.mail'].sudo().search([('mailing_id', '=', mailing.id)])
        self.assertFalse(mails, 'Should have auto-deleted the <mail.mail>')

    @users('__system__', 'marketing')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_send_mailing_tracking_disabled(self):
        """ Half of the recipients are located in a country for which tracking
        is disabled (see 'mass_mailing.disable_tracking'). """
        country_fr, country_be = self.env.ref('base.fr'), self.env.ref('base.be')
        mailing_list = self.env['mailing.list'].sudo().create({
            'name': 'Tracking List',
            'contact_ids': [(0, 0, {
                'name': 'Recipient %s' % x,
                'email': 'rec.%s@example.com' % x,
                'country_id': (country_fr if x % 2 else country_be).id,
            }) for x in range(0, 50)],
        })
        mailing = self.env['mailing.mailing'].create({
            'name': 'Test',
            'subject': 'Test',
            'body_html': '<p>Hello <a role="button" href="https://www.example.com/foo/bar?baz=qux">quux</a><a role="button" href="/unsubscribe_from_list">Unsubscribe</a></p>',
            'reply_to_mode': 'new',
            'mailing_model_id': self.ref('mass_mailing.model_mailing_list'),
            'contact_list_ids': [(4, mailing_list.id)],
        })

        # patch rather than set the parameter: 'set_param' clears the ormcaches
        # during the measured run
        with patch.object(self.registry['mailing.mailing'], '_get_tracking_disabled_config',
                          lambda self: (False, {'FR'})), \
             self.assertQueryCount(__system__=1105, marketing=1106):
            mailing.action_send_mail()

        self.assertEqual(mailing.sent, 50)
        self.assertEqual(mailing.delivered, 50)


@tagged('mail_performance', 'post_install', '-at_install')
class TestMassMailBlPerformance(TestMassMailPerformanceBase):

    def setUp(self):
        """ In this setup we prepare 20 blacklist entries. We therefore add
        20 recipients compared to first test in order to have comparable results. """
        super(TestMassMailBlPerformance, self).setUp()
        values = [{
            'name': 'Recipient %s' % x,
            'email_from': 'Recipient <rec.%s@example.com>' % x,
        } for x in range(0, 62)]
        self.mm_recs = self.env['mailing.performance.blacklist'].create(values)

        for x in range(1, 13):
            self.env['mail.blacklist'].create({
                'email': 'rec.%s@example.com' % (x * 5)
            })
        self.env.flush_all()

    @users('__system__', 'marketing')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    def test_send_mailing_w_bl(self):
        mailing = self.env['mailing.mailing'].create({
            'name': 'Test',
            'subject': 'Test',
            'body_html': '<p>Hello <a role="button" href="https://www.example.com/foo/bar?baz=qux">quux</a><a role="button" href="/unsubscribe_from_list">Unsubscribe</a></p>',
            'reply_to_mode': 'new',
            'mailing_model_id': self.ref('test_mass_mailing.model_mailing_performance_blacklist'),
            'mailing_domain': [('id', 'in', self.mm_recs.ids)],
        })

        # runbot needs +102 compared to local
        with self.assertQueryCount(__system__=1319, marketing=1320):  # 1217, 1218
            mailing.action_send_mail()

        self.assertEqual(mailing.sent, 50)
        self.assertEqual(mailing.delivered, 50)

        cancelled_mail_count = self.env['mail.mail'].sudo().search([('mailing_id', '=', mailing.id)])
        self.assertEqual(len(cancelled_mail_count), 12, 'Should not have auto deleted the blacklisted emails')
