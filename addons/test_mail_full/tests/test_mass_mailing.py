# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail_full.tests.common import TestMailFullCommon
from odoo.tests.common import users
from odoo.tools import config, mute_logger
from odoo.tests import tagged


@tagged('mass_mailing')
class TestMassMailing(TestMailFullCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMassMailing, cls).setUpClass()

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_w_blacklist_opt_out(self):
        # TDE FIXME: better URLs check for unsubscribe / view (res_id + email + correct parse of url)
        mailing = self.mailing_bl.with_user(self.env.user)

        jinja_html = '''
<div>
    <p>Hello <span class="text-muted">${object.name}</span></p>
    <p>
        Here are your personal links
        <a href="http://www.example.com">External link</a>
        <a href="/event/dummy-event-0">Internal link</a>
        <a role="button" href="/unsubscribe_from_list" class="btn btn-link">Unsubscribe link</a>
        <a href="/view">
            View link
        </a>
    </p>
</div>'''

        mailing.write({
            'preview': 'Hi ${object.name} :)',
            'body_html': jinja_html,
            'mailing_model_id': self.env['ir.model']._get('mailing.test.optout').id,
        })
        recipients = self._create_test_blacklist_records(model='mailing.test.optout', count=10)

        # optout records 1 and 2
        (recipients[1] | recipients[2]).write({'opt_out': True})
        # blacklist records 3 and 4
        self.env['mail.blacklist'].create({'email': recipients[3].email_normalized})
        self.env['mail.blacklist'].create({'email': recipients[4].email_normalized})

        mailing.write({'mailing_domain': [('id', 'in', recipients.ids)]})
        mailing.action_put_in_queue()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing._process_mass_mailing_queue()

        for recipient in recipients:
            recipient_info = {
                'email': recipient.email_normalized,
                'content': 'Hello <span class="text-muted">%s</span' % recipient.name}
            if recipient in recipients[1] | recipients[2]:
                recipient_info['state'] = 'ignored'
            elif recipient in recipients[3] | recipients[4]:
                recipient_info['state'] = 'ignored'
            else:
                email = self._find_sent_mail_wemail(recipient.email_normalized)
                # preview correctly integrated rendered jinja
                self.assertIn(
                    'Hi %s :)' % recipient.name,
                    email['body'])
                # rendered unsubscribe
                self.assertIn(
                    'http://localhost:%s/mail/mailing/%s/unsubscribe' % (config['http_port'], mailing.id),
                    email['body'])
                # rendered view
                self.assertIn(
                    'http://localhost:%s/mailing/%s/view' % (config['http_port'], mailing.id),
                    email['body'])

            self.assertMailTraces([recipient_info], mailing, recipient, check_mail=True, author=self.env.user.partner_id)

        self.assertEqual(mailing.ignored, 4)
