# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from odoo.addons.test_mail_full.tests.common import TestMailFullCommon
from odoo.tests.common import users
from odoo.tools import mute_logger
from odoo.tests import tagged


@tagged('mass_mailing')
class TestMassMailing(TestMailFullCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMassMailing, cls).setUpClass()

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_w_blacklist_opt_out(self):
        mailing = self.env['mailing.mailing'].browse(self.mailing_bl.ids)

        mailing.write({'mailing_model_id': self.env['ir.model']._get('mailing.test.optout').id})
        recipients = self._create_mailing_test_records(model='mailing.test.optout', count=10)

        # optout records 1 and 2
        (recipients[1] | recipients[2]).write({'opt_out': True})
        # blacklist records 3 and 4
        self.env['mail.blacklist'].create({'email': recipients[3].email_normalized})
        self.env['mail.blacklist'].create({'email': recipients[4].email_normalized})
        # have a duplicate email for 9
        recipient_dup_1 = recipients[9].copy()
        # have a void mail
        recipient_void_1 = self.env['mailing.test.optout'].create({'name': 'TestRecord_void_1'})
        # have a falsy mail
        recipient_falsy_1 = self.env['mailing.test.optout'].create({
            'name': 'TestRecord_falsy_1',
            'email_from': 'falsymail'
        })
        recipients_all = recipients + recipient_dup_1 + recipient_void_1 + recipient_falsy_1

        mailing.write({'mailing_domain': [('id', 'in', recipients_all.ids)]})
        mailing.action_put_in_queue()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing._process_mass_mailing_queue()

        for recipient in recipients_all:
            recipient_info = {
                'email': recipient.email_normalized,
                'content': 'Hello %s' % recipient.name}
            # opt-out: ignored (cancel mail)
            if recipient in recipients[1] | recipients[2]:
                recipient_info['state'] = 'ignored'
            # blacklisted: ignored (cancel mail)
            elif recipient in recipients[3] | recipients[4]:
                recipient_info['state'] = 'ignored'
            # duplicates: ignored (cancel mail)
            elif recipient == recipient_dup_1:
                recipient_info['state'] = 'ignored'
            # void: ignored (cancel mail)
            elif recipient == recipient_void_1:
                recipient_info['state'] = 'ignored'
            # falsy: ignored (cancel mail)
            elif recipient == recipient_falsy_1:
                recipient_info['state'] = 'ignored'
                recipient_info['email'] = recipient.email_from  # normalized is False but email should be falsymail
            else:
                email = self._find_sent_mail_wemail(recipient.email_normalized)
                # preview correctly integrated rendered jinja
                self.assertIn(
                    'Hi %s :)' % recipient.name,
                    email['body'])
                # rendered unsubscribe
                self.assertIn(
                    '%s/mail/mailing/%s/unsubscribe' % (mailing.get_base_url(), mailing.id),
                    email['body'])
                unsubscribe_href = self._get_href_from_anchor_id(email['body'], "url6")
                unsubscribe_url = werkzeug.urls.url_parse(unsubscribe_href)
                unsubscribe_params = unsubscribe_url.decode_query().to_dict(flat=True)
                self.assertEqual(int(unsubscribe_params['res_id']), recipient.id)
                self.assertEqual(unsubscribe_params['email'], recipient.email_normalized)
                self.assertEqual(
                    mailing._unsubscribe_token(unsubscribe_params['res_id'], (unsubscribe_params['email'])),
                    unsubscribe_params['token']
                )
                # rendered view
                self.assertIn(
                    '%s/mailing/%s/view' % (mailing.get_base_url(), mailing.id),
                    email['body'])
                view_href = self._get_href_from_anchor_id(email['body'], "url6")
                view_url = werkzeug.urls.url_parse(view_href)
                view_params = view_url.decode_query().to_dict(flat=True)
                self.assertEqual(int(view_params['res_id']), recipient.id)
                self.assertEqual(view_params['email'], recipient.email_normalized)
                self.assertEqual(
                    mailing._unsubscribe_token(view_params['res_id'], (view_params['email'])),
                    view_params['token']
                )

            self.assertMailTraces(
                [recipient_info], mailing, recipient,
                mail_links_info=[[
                    ('url0', 'https://www.odoo.tz/my/%s' % recipient.name, True, {}),
                    ('url1', 'https://www.odoo.be', True, {}),
                    ('url2', 'https://www.odoo.com', True, {}),
                    ('url3', 'https://www.odoo.eu', True, {}),
                    ('url4', 'https://www.example.com/foo/bar?baz=qux', True, {'baz': 'qux'}),
                    ('url5', '%s/event/dummy-event-0' % mailing.get_base_url(), True, {}),
                    # view is not shortened and parsed at sending
                    ('url6', '%s/view' % mailing.get_base_url(), False, {}),
                    ('url7', 'mailto:test@odoo.com', False, {}),
                    # unsubscribe is not shortened and parsed at sending
                    ('url8', '%s/unsubscribe_from_list' % mailing.get_base_url(), False, {}),
                ]],
                check_mail=True,)

        # sent: 13, 2 bl, 2 opt-out, 3 invalid -> 6 remaining
        self.assertMailingStatistics(mailing, expected=13, delivered=6, sent=6, ignored=7)
