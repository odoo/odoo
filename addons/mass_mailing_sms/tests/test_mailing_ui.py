# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged, users


@tagged('post_install', '-at_install', 'mail_activity')
class TestMailingUi(HttpCase):

    @users('admin')
    def test_tour_mailing_activities_split(self):
        """ Activities linked to mailing.mailing records can appear either in the
            'Email Marketing', either in the 'SMS Marketing' category, depending on
            the value of the field mailing_type of the record it is linked to. This
            test ensures that:
                - activities linked to records with mailing_type set to mail are listed
                  in the 'Email Marketing' category
                - activities linked to records with mailing_type set to sms are listed
                  in the 'SMS Marketing' category
        """
        user_admin = self.env.ref('base.user_admin')
        user_admin.write({
            'email': 'mitchell.admin@example.com',
        })
        sms_rec, email_rec = self.env['mailing.mailing'].create([
            {
                'body_plaintext': 'Some sms spam',
                'mailing_type': 'sms',
                'name': 'SMS record with an activity',
                'subject': 'New SMS!',
            }, {
                'body_html': '<p>Some email spam</p>',
                'mailing_type': 'mail',
                'name': 'Email record with an activity',
                'subject': 'New Email!',
            }
        ])

        sms_rec.activity_schedule(act_type_xmlid='mail.mail_activity_data_todo', user_id=user_admin.id)
        email_rec.activity_schedule(act_type_xmlid='mail.mail_activity_data_todo', user_id=user_admin.id)

        # Ensure that both activities appear in the systray and that clicking on
        # one activity opens a view where the other activity isn't listed
        self.start_tour("/odoo", 'mailing_activities_split', login="admin")
