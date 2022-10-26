# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import lxml.html

from odoo.addons.test_mass_mailing.tests.common import TestMassMailCommon
from odoo.fields import Command
from odoo.tests.common import users
from odoo.tools import mute_logger


class TestMailingTest(TestMassMailCommon):

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_render_mixin')
    def test_mailing_test_button(self):
        mailing = self.env['mailing.mailing'].create({
            'name': 'TestButton',
            'subject': 'Subject {{ object.name }}',
            'preview': 'Preview {{ object.name }}',
            'state': 'draft',
            'mailing_type': 'mail',
            'body_html': '<p>Hello <t t-out="object.name"/></p>',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
        })
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

    def test_mailing_test_equals_reality(self):
        """
        Check that both test and real emails will format the qweb and inline placeholders correctly in body and subject.
        """
        contact_list = self.env['mailing.list'].create({
            'name': 'Testers',
            'contact_ids': [Command.create({
                'name': 'Mitchell Admin',
                'email': 'real@real.com',
            })],
        })

        mailing = self.env['mailing.mailing'].create({
            'name': 'TestButton',
            'subject': 'Subject {{ object.name }} <t t-out="object.name"/>',
            'state': 'draft',
            'mailing_type': 'mail',
            'body_html': '<p>Hello {{ object.name }} <t t-out="object.name"/></p>',
            'mailing_model_id': self.env['ir.model']._get('mailing.list').id,
            'contact_list_ids': [contact_list.id],
        })
        mailing_test = self.env['mailing.mailing.test'].create({
            'email_to': 'test@test.com',
            'mass_mailing_id': mailing.id,
        })

        with self.mock_mail_gateway():
            mailing_test.send_mail_test()

        expected_subject = 'Subject Mitchell Admin <t t-out="object.name"/>'
        expected_body = 'Hello {{ object.name }} Mitchell Admin'

        self.assertSentEmail(self.env.user.partner_id, ['test@test.com'],
            subject=expected_subject,
            body_content=expected_body)

        with self.mock_mail_gateway():
            # send the mailing
            mailing.action_launch()
            self.env.ref('mass_mailing.ir_cron_mass_mailing_queue').method_direct_trigger()

        self.assertSentEmail(self.env.user.partner_id, ['real@real.com'],
            subject=expected_subject,
            body_content=expected_body)
