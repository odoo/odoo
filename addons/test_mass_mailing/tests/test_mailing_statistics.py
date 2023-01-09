# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.test_mass_mailing.data.mail_test_data import MAIL_TEMPLATE
from odoo.addons.test_mass_mailing.tests.common import TestMassMailCommon
from odoo.tests.common import users
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('digest', 'mass_mailing')
class TestMailingStatistics(TestMassMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailingStatistics, cls).setUpClass()

        cls.user_marketing_2 = mail_new_test_user(
            cls.env,
            groups='base.group_user,base.group_partner_manager,mass_mailing.group_mass_mailing_user',
            login='user_marketing_2',
            name='Marie Marketing',
            signature='--\nMarie'
        )

    @users('user_marketing')
    @mute_logger('odoo.addons.mass_mailing.models.mailing', 'odoo.addons.mail.models.mail_mail', 'odoo.addons.mail.models.mail_thread')
    def test_mailing_statistics(self):
        target_records = self._create_mailing_test_records(model='mailing.test.blacklist', count=10)
        mailing = self.env['mailing.mailing'].browse(self.mailing_bl.ids)
        mailing.write({'mailing_domain': [('id', 'in', target_records.ids)], 'user_id': self.user_marketing_2.id})
        mailing.action_put_in_queue()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing.action_send_mail()

        # simulate some replies and clicks
        self.gateway_mail_reply_wrecord(MAIL_TEMPLATE, target_records[0], use_in_reply_to=True)
        self.gateway_mail_reply_wrecord(MAIL_TEMPLATE, target_records[1], use_in_reply_to=True)
        self.gateway_mail_reply_wrecord(MAIL_TEMPLATE, target_records[2], use_in_reply_to=True)
        self.gateway_mail_click(mailing, target_records[0], 'https://www.odoo.be')
        self.gateway_mail_click(mailing, target_records[2], 'https://www.odoo.be')
        self.gateway_mail_click(mailing, target_records[3], 'https://www.odoo.be')

        # check mailing statistics
        self.assertEqual(mailing.clicked, 3)
        self.assertEqual(mailing.delivered, 10)
        self.assertEqual(mailing.opened, 4)
        self.assertEqual(mailing.opened_ratio, 40)
        self.assertEqual(mailing.replied, 3)
        self.assertEqual(mailing.replied_ratio, 30)
        self.assertEqual(mailing.sent, 10)

        with self.mock_mail_gateway(mail_unlink_sent=True):
            mailing._action_send_statistics()

        self.assertEqual(len(self._new_mails), 1, "Mailing: a mail should have been created for statistics")
        mail = self._new_mails[0]
        # test email values
        self.assertEqual(mail.author_id, self.user_marketing_2.partner_id)
        self.assertEqual(mail.email_from, self.user_marketing_2.email_formatted)
        self.assertEqual(mail.email_to, self.user_marketing_2.email_formatted)
        self.assertEqual(mail.reply_to, self.company_admin.partner_id.email_formatted)
        self.assertEqual(mail.state, 'outgoing')
        # test body content: KPIs
        body_html = html.fromstring(mail.body_html)
        kpi_values = body_html.xpath('//div[@data-field="mail"]//*[hasclass("kpi_value")]/text()')
        self.assertEqual(
            [t.strip().strip('%') for t in kpi_values],
            ['100', str(mailing.opened_ratio), str(mailing.replied_ratio)]
        )
        # test body content: clicks (a bit hackish but hey we are in stable)
        kpi_click_values = body_html.xpath('//div[hasclass("global_layout")]/table//tr[contains(@style,"color: #888888")]/td[contains(@style,"width: 30%")]/text()')
        first_link_value = int(kpi_click_values[0].strip().split()[1].strip('()'))
        self.assertEqual(first_link_value, mailing.clicked)

    @users('user_marketing')
    @mute_logger('odoo.addons.mass_mailing.models.mailing', 'odoo.addons.mail.models.mail_mail', 'odoo.addons.mail.models.mail_thread')
    def test_mailing_statistics_wo_user(self):
        target_records = self._create_mailing_test_records(model='mailing.test.blacklist', count=10)
        mailing = self.env['mailing.mailing'].browse(self.mailing_bl.ids)
        mailing.write({'mailing_domain': [('id', 'in', target_records.ids)], 'user_id': False})
        mailing.action_put_in_queue()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing.action_send_mail()

        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing._action_send_statistics()

        self.assertEqual(len(self._new_mails), 1, "Mailing: a mail should have been created for statistics")
        mail = self._new_mails[0]
        # test email values
        self.assertEqual(mail.author_id, self.user_marketing.partner_id)
        self.assertEqual(mail.email_from, self.user_marketing.email_formatted)
        self.assertEqual(mail.email_to, self.user_marketing.email_formatted)
        self.assertEqual(mail.reply_to, self.company_admin.partner_id.email_formatted)
        self.assertEqual(mail.state, 'outgoing')
