# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.link_tracker.tests.common import MockLinkTracker
from odoo.addons.mail.tests.common import MailCase, mail_new_test_user
from odoo.tests.common import SavepointCase


class MassMailCase(MailCase, MockLinkTracker):

    def _find_mail_mail_wemail(self, email_to, state, author=None):
        for mail in self._new_mails:
            if author is not None and mail.author_id != author:
                continue
            if mail.state != state:
                continue
            if (mail.email_to == email_to and not mail.recipient_ids) or (not mail.email_to and mail.recipient_ids.email) == email_to:
                break
        else:
            raise AssertionError('mail.mail not found for email_to %s / state %s in %s' % (email_to, state, repr([m.email_to for m in self._new_mails])))
        return mail

    def _find_mail_mail_wrecord(self, record):
        for mail in self._new_mails:
            if mail.model == record._name and mail.res_id == record.id:
                break
        else:
            raise AssertionError('mail.mail not found for record %s in %s' % (record, repr([m.email_to for m in self._new_mails])))
        return mail

    def assertMailMailWEmails(self, emails, state, content, fields_values=None):
        """ Will check in self._new_mails to find a sent mail.mail. To use with
        mail gateway mock.

        :param emails: list of emails;
        :param state: state of mail.mail;
        :param content: content to check for each email;
        :param fields_values: specific value to check on the mail.mail record;
        """
        for email_to in emails:
            sent_mail = self._find_mail_mail_wemail(email_to, state)
            if content:
                self.assertIn(content, sent_mail.body_html)
            for fname, fvalue in (fields_values or {}).items():
                self.assertEqual(sent_mail[fname], fvalue)

    def assertMailTraces(self, recipients_info, mailing, records, check_mail=True):
        """ Check content of traces.

        :param recipients_info: list[{
            'partner': res.partner record (may be empty),
            'email': email used when sending email (may be empty, computed based on partner),
            'state': outgoing / sent / open / reply / error / cancel (sent by default),
            'record: linked record,
            'content': UDPATE ME
            'failure_type': optional: UPDATE ME
            }, { ... }]
        """
        traces = self.env['mailing.trace'].search([
            ('mass_mailing_id', 'in', mailing.ids),
            ('res_id', 'in', records.ids)
        ])

        # ensure trace coherency
        self.assertTrue(all(s.model == records._name for s in traces))
        self.assertEqual(set(s.res_id for s in traces), set(records.ids))

        # check each traces
        for recipient_info in recipients_info:
            partner = recipient_info.get('partner', self.env['res.partner'])
            email = recipient_info.get('email')
            state = recipient_info.get('state', 'sent')
            record = recipient_info.get('record')
            content = recipient_info.get('content')
            if email is None and partner:
                email = partner.email_normalized

            recipient_trace = traces.filtered(
                lambda t: t.email == email and t.state == state and (t.res_id == record.id if record else True)
            )
            self.assertTrue(
                len(recipient_trace) == 1,
                'MailTrace: email %s (recipient %s, state: %s, record: %s): found %s records (1 expected)' % (email, partner, state, record, len(recipient_trace))
            )

            if check_mail:
                fields_values = {'mailing_id': mailing}
                if 'failure_type' in recipient_info:
                    fields_values['failure_type'] = recipient_info['failure_type']

                if state == 'sent':
                    self.assertMailMailWEmails([email], 'sent', content, fields_values=fields_values)
                elif state == 'ignored':
                    self.assertMailMailWEmails([email], 'cancel', content, fields_values=fields_values)
                elif state == 'exception':
                    self.assertMailMailWEmails([email], 'exception', content, fields_values=fields_values)
                elif state == 'canceled':
                    self.assertMailMailWEmails([email], 'canceled', content, fields_values=fields_values)
                else:
                    raise NotImplementedError()


class TestMassMailCommon(SavepointCase, MassMailCase):

    @classmethod
    def setUpClass(cls):
        super(TestMassMailCommon, cls).setUpClass()

        cls.user_marketing = mail_new_test_user(
            cls.env, login='user_marketing',
            groups='base.group_user,base.group_partner_manager,mass_mailing.group_mass_mailing_user',
            name='Martial Marketing', signature='--\nMartial')

        cls.email_reply_to = 'MyCompany SomehowAlias <test.alias@test.mycompany.com>'

    @classmethod
    def _create_mailing_list(cls):
        """ Shortcut to create mailing lists. Currently hardcoded, maybe evolve
        in a near future. """
        cls.mailing_list_1 = cls.env['mailing.list'].with_context(cls._test_context).create({
            'name': 'List1',
            'contact_ids': [
                (0, 0, {'name': 'Déboulonneur', 'email': 'fleurus@example.com'}),
                (0, 0, {'name': 'Gorramts', 'email': 'gorramts@example.com'}),
                (0, 0, {'name': 'Ybrant', 'email': 'ybrant@example.com'}),
            ]
        })
        cls.mailing_list_2 = cls.env['mailing.list'].with_context(cls._test_context).create({
            'name': 'List2',
            'contact_ids': [
                (0, 0, {'name': 'Gilberte', 'email': 'gilberte@example.com'}),
                (0, 0, {'name': 'Gilberte En Mieux', 'email': 'gilberte@example.com'}),
                (0, 0, {'name': 'Norbert', 'email': 'norbert@example.com'}),
                (0, 0, {'name': 'Ybrant', 'email': 'ybrant@example.com'}),
            ]
        })
