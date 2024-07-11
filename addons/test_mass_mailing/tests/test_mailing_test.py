# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import lxml.html

from odoo.addons.test_mass_mailing.tests.common import TestMassMailCommon
from odoo.fields import Command
from odoo.tests.common import users, tagged
from odoo.tools import mute_logger


@tagged('mailing_manage')
class TestMailingTest(TestMassMailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_records = cls.env['mailing.test.blacklist'].create([
            {
                'email_from': f'test.mailing.{idx}@test.example.com',
                'name': f'Test Mailing {idx}',
                'user_id': cls.user_marketing.id,
            }
            for idx in range(5)
        ])
        cls.test_mailing_bl = cls.env['mailing.mailing'].create({
            'body_html': '<p>Hello <t t-out="object.name"/></p>',
            'mailing_domain': [('id', 'in', cls.test_records.ids)],
            'mailing_model_id': cls.env['ir.model']._get_id('mailing.test.blacklist'),
            'mailing_type': 'mail',
            'name': 'TestButton',
            'preview': 'Preview {{ object.name }}',
            'subject': 'Subject {{ object.name }}',
        })

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_render_mixin')
    def test_mailing_test_button(self):
        mailing = self.test_mailing_bl.with_env(self.env)
        mailing_test = self.env['mailing.mailing.test'].create({
            'email_to': 'test@test.com',
            'mass_mailing_id': mailing.id,
        })

        with self.mock_mail_gateway():
            mailing_test.send_mail_test()

        # not great but matches send_mail_test, maybe that should be a method
        # on mailing_test?
        record = self.env[mailing.mailing_model_real].search([], limit=1)
        first_child = lxml.html.fromstring(self._mails.pop()['body']).xpath('//body/*[1]')[0]
        self.assertEqual(first_child.tag, 'div')
        self.assertIn('display:none', first_child.get('style'),
                      "the preview node should be hidden")
        self.assertEqual(first_child.text.strip(), "Preview " + record.name,
                         "the preview node should contain the preview text")

        # Test if bad inline_template in the subject raises an error
        mailing.write({'subject': 'Subject {{ object.name_id.id }}'})
        with self.mock_mail_gateway(), self.assertRaises(Exception):
            mailing_test.send_mail_test()

        # Test if bad inline_template in the body raises an error
        mailing.write({
            'subject': 'Subject {{ object.name }}',
            'body_html': '<p>Hello <t t-out="object.name_id.id"/></p>',
        })
        with self.mock_mail_gateway(), self.assertRaises(Exception):
            mailing_test.send_mail_test()

        # Test if bad inline_template in the preview raises an error
        mailing.write({
            'body_html': '<p>Hello <t t-out="object.name"/></p>',
            'preview': 'Preview {{ object.name_id.id }}',
        })
        with self.mock_mail_gateway(), self.assertRaises(Exception):
            mailing_test.send_mail_test()

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_render_mixin')
    def test_mailing_test_button_links(self):
        """This tests that the link provided by the View in Browser snippet is correctly replaced
        when sending a test mailing while the Unsubscribe button's link isn't, to preserve the testing route
        /unsubscribe_from_list.
        This also checks that other links containing the /view route aren't replaced along the way.
        """
        mailing = self.test_mailing_bl.with_env(self.env)
        mailing_test = self.env['mailing.mailing.test'].create({
            'email_to': 'test@test.com',
            'mass_mailing_id': mailing.id,
        })
        # Test if link snippets are correctly converted
        mailing.write({
            'body_html':
                '''<p>
                Hello <a href="http://www.example.com/view">World<a/>
                    <div class="o_snippet_view_in_browser o_mail_snippet_general pt16 pb16" style="text-align: center; padding-left: 15px; padding-right: 15px;">
                        <a href="/view">
                            View Online
                        </a>
                    </div>
                    <div class="o_mail_footer_links">
                        <a role="button" href="/unsubscribe_from_list" class="btn btn-link">Unsubscribe</a>
                    </div>
                </p>''',
            'preview': 'Preview {{ object.name }}',
            'subject': 'Subject {{ object.name }}',
        })

        with self.mock_mail_gateway():
            mailing_test.send_mail_test()

        body_html = self._mails.pop()['body']
        self.assertIn(f'/mailing/{mailing.id}/view', body_html)  # Is replaced
        self.assertIn('/unsubscribe_from_list', body_html)  # Isn't replaced
        self.assertIn('http://www.example.com/view', body_html)  # Isn't replaced

    def test_mailing_test_equals_reality(self):
        """ Check that both test and real emails will format the qweb and inline
        placeholders correctly in body and subject. """
        mailing = self.test_mailing_bl.with_env(self.env)
        mailing.write({
            'body_html': '<p>Hello {{ object.name }} <t t-out="object.name"/></p>',
            'subject': 'Subject {{ object.name }} <t t-out="object.name"/>',
        })
        mailing_test = self.env['mailing.mailing.test'].create({
            'email_to': 'test@test.com',
            'mass_mailing_id': mailing.id,
        })

        with self.mock_mail_gateway():
            mailing_test.send_mail_test()

        expected_test_record = self.env[mailing.mailing_model_real].search([], limit=1)
        self.assertEqual(expected_test_record, self.test_records[0], 'Should take first found one')
        expected_subject = f'Subject {expected_test_record.name} <t t-out="object.name"/>'
        expected_body = 'Hello {{ object.name }}' + f' {expected_test_record.name}'

        self.assertSentEmail(self.env.user.partner_id, ['test@test.com'],
            subject=expected_subject,
            body_content=expected_body)

        with self.mock_mail_gateway():
            # send the mailing
            mailing.action_launch()
            self.env.ref('mass_mailing.ir_cron_mass_mailing_queue').method_direct_trigger()

        self.assertSentEmail(
            self.env.user.partner_id,
            [expected_test_record.email_from],
            subject=expected_subject,
            body_content=expected_body,
        )
