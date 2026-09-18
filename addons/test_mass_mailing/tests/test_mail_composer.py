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
        subjects = {}
        for use_exclusion_list in (True, False):
            mass_mailing_subject = f'Test Create Mass Mailing From Composer (use_exclusion_list: {use_exclusion_list})'
            composer = self.env['mail.compose.message'].with_context(
                self._get_web_context(self.test_records)
            ).create({
                'body': '<p>Body</p>',
                'subject': mass_mailing_subject,
                'mass_mailing_create': True,
                'use_exclusion_list': use_exclusion_list,
            })
            composer._action_send_mail()
            subjects[mass_mailing_subject] = use_exclusion_list
        mailings = self.env['mailing.mailing'].search([('subject', 'in', list(subjects))])
        mailings_by_subject = {m.subject: m for m in mailings}
        for mass_mailing_subject, use_exclusion_list in subjects.items():
            mailing = mailings_by_subject[mass_mailing_subject]
            self.assertTrue(mailing)
            self.assertEqual(mailing.body_html, '<p>Body</p>')
            self.assertEqual(mailing.mailing_domain, f"[('id', 'in', {self.test_records.ids})]")
            self.assertEqual(mailing.mailing_model_name, self.test_record._name)
            self.assertEqual(mailing.sent_date, fields.Datetime.now())
            self.assertEqual(mailing.state, 'done')
            self.assertEqual(mailing.use_exclusion_list, use_exclusion_list)
