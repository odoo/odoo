# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.tests import freeze_time, tagged, users
from odoo.tools import mute_logger

from odoo.addons.test_mail.tests.test_mail_composer import TestMailComposer
from odoo.addons.test_mass_mailing.tests import common


@tagged('mail_composer')
class TestMailComposerMassMailing(TestMailComposer, common.TestMassMailCommon):

    @users('user_marketing')
    @mute_logger('odoo.addons.mass_mailing.models.mailing')
    @freeze_time('2025-08-06 15:02:00')
    def test_mail_composer_mailing_creation(self):
        """Check mailing configuration created through the mail composer."""
        for use_exclusion_list in (True, False):
            mass_mailing_name = f'Test Create Mass Mailing From Composer (use_exclusion_list: {use_exclusion_list})'
            composer = self.env['mail.compose.message'].with_context(
                self._get_web_context(self.test_records)
            ).create({
                'body': '<p>Body</p>',
                'mass_mailing_name': mass_mailing_name,
                'subject': 'Test',
                'use_exclusion_list': use_exclusion_list,
            })
            composer._action_send_mail()
            mailing = self.env['mailing.mailing'].search([('name', '=', mass_mailing_name)])
            self.assertTrue(mailing)
            self.assertEqual(mailing.body_html, '<p>Body</p>')
            self.assertEqual(mailing.mailing_domain, f"[('id', 'in', {self.test_records.ids})]")
            self.assertEqual(mailing.mailing_model_name, self.test_record._name)
            self.assertEqual(mailing.sent_date, fields.Datetime.now())
            self.assertEqual(mailing.state, 'done')
            self.assertEqual(mailing.subject, 'Test')
            self.assertEqual(mailing.use_exclusion_list, use_exclusion_list)
