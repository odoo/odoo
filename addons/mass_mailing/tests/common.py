# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import random
import re
import werkzeug

from unittest.mock import patch

from odoo.tools import email_normalize, mail
from odoo.addons.link_tracker.tests.common import MockLinkTracker
from odoo.addons.mail.tests.common import MailCase, MailCommon, mail_new_test_user
from odoo.sql_db import Cursor


class MassMailCase(MailCase, MockLinkTracker):

    # ------------------------------------------------------------
    # ASSERTS
    # ------------------------------------------------------------

    def assertMailingStatistics(self, mailing, **kwargs):
        """ Helper to assert mailing statistics fields. As we have many of them
        it helps lessening test asserts. """
        if not kwargs.get('expected'):
            kwargs['expected'] = len(mailing.mailing_trace_ids)
        if not kwargs.get('delivered'):
            kwargs['delivered'] = len(mailing.mailing_trace_ids)
        for fname in ['scheduled', 'expected', 'sent', 'delivered',
                      'opened', 'replied', 'clicked',
                      'canceled', 'failed', 'bounced']:
            self.assertEqual(
                mailing[fname], kwargs.get(fname, 0),
                'Mailing %s statistics failed: got %s instead of %s' % (fname, mailing[fname], kwargs.get(fname, 0))
            )

    def assertMailTraces(self, recipients_info, mailing, records,
                         check_mail=True, is_cancel_not_sent=True, sent_unlink=False,
                         author=None, mail_links_info=None):
        """ Check content of traces. Traces are fetched based on a given mailing
        and records. Their content is compared to recipients_info structure that
        holds expected information. Links content may be checked, notably to
        assert shortening or unsubscribe links. Mail.mail records may optionally
        be checked.

        :param recipients_info: list[{
            # TRACE
            'email': (normalized) email used when sending email and stored on
              trace. May be empty, computed based on partner;
            'failure_type': optional failure type;
            'failure_reason': optional failure reason;
            'partner': res.partner record (may be empty),
            'record: linked record,
            'trace_status': outgoing / sent / open / reply / bounce / error / cancel (sent by default),
            # MAIL.MAIL
            'content': optional content that should be present in mail.mail body_html;
            'email_to_mail': optional email used for the mail, when different from the
              one stored on the trace itself (see 'email_to' in assertMailMail);
            'email_to_recipients': optional email used ofr the outgoing email,
              see 'assertSentEmail';
            'failure_type': propagated from trace;
            'failure_reason': propagated from trace;
            'mail_values': other mail.mail values for assertMailMail;
            }, { ... }]

        :param mailing: a mailing.mailing record from which traces have been
          generated;
        :param records: records given to mailing that generated traces. It is
          used notably to find traces using their IDs;
        :param check_mail: if True, also check mail.mail records that should be
          linked to traces unless not sent (trace_status == 'cancel');
        :param is_cancel_not_sent: if True, also check that no mail.mail/mail.message
          related to "cancel trace" have been created and disable check_mail for those.
        :param sent_unlink: it True, sent mail.mail are deleted and we check gateway
          output result instead of actual mail.mail records;
        :param mail_links_info: if given, should follow order of ``recipients_info``
          and give details about links. See ``assertLinkShortenedHtml`` helper for
          more details about content to give.
          Not tested for mail with trace status == 'cancel' if is_cancel_not_sent;
        :param author: author of sent mail.mail;
        """
        # map trace state to email state
        state_mapping = {
            'sent': 'sent',
            'open': 'sent',  # opened implies something has been sent
            'reply': 'sent',  # replied implies something has been sent
            'error': 'exception',
            'cancel': 'cancel',
            'bounce': 'cancel',
        }

        traces = self.env['mailing.trace'].search([
            ('mass_mailing_id', 'in', mailing.ids),
            ('res_id', 'in', records.ids)
        ])
        debug_info = '\n'.join(
            f'Trace: to {t.email} - state {t.trace_status} - res_id {t.res_id}'
            for t in traces
        )

        # ensure trace coherency
        self.assertTrue(all(s.model == records._name for s in traces))
        self.assertEqual(set(s.res_id for s in traces), set(records.ids))

        # check each traces
        if not mail_links_info:
            mail_links_info = [None] * len(recipients_info)
        for recipient_info, link_info, record in zip(recipients_info, mail_links_info, records):
            # check input
            invalid = set(recipient_info.keys()) - {
                'content',
                # email_to
                'email', 'email_to_mail', 'email_to_recipients',
                # mail.mail
                'mail_values',
                # email
                'email_values',
                # trace
                'partner', 'record', 'trace_status',
                'failure_type', 'failure_reason',
            }
            if invalid:
                raise AssertionError(f"assertMailTraces: invalid input {invalid}")

            # recipients
            partner = recipient_info.get('partner', self.env['res.partner'])
            email = recipient_info.get('email')
            if email is None and partner:
                email = partner.email_normalized
            email_to_mail = recipient_info.get('email_to_mail') or email
            email_to_recipients = recipient_info.get('email_to_recipients')
            # trace
            failure_type = recipient_info.get('failure_type')
            failure_reason = recipient_info.get('failure_reason')
            status = recipient_info.get('trace_status', 'sent')
            # content
            content = recipient_info.get('content')
            record = record or recipient_info.get('record')

            recipient_trace = traces.filtered(
                lambda t: (t.email == email or (not email and not t.email)) and \
                          t.trace_status == status and \
                          (t.res_id == record.id if record else True)
            )
            self.assertTrue(
                len(recipient_trace) == 1,
                'MailTrace: email %s (recipient %s, status: %s, record: %s): found %s records (1 expected)\n%s' % (
                    email, partner, status, record,
                    len(recipient_trace), debug_info)
            )
            mail_not_created = is_cancel_not_sent and recipient_trace.trace_status == 'cancel'
            self.assertTrue(mail_not_created or bool(recipient_trace.mail_mail_id_int))
            if 'failure_type' in recipient_info or status in ('error', 'cancel', 'bounce'):
                self.assertEqual(recipient_trace.failure_type, failure_type)
            if 'failure_reason' in recipient_info:
                self.assertEqual(recipient_trace.failure_reason, failure_reason)
            if mail_not_created:
                self.assertFalse(recipient_trace.mail_mail_id_int)
                self.assertFalse(self.env['mail.mail'].sudo().search(
                    [('model', '=', record._name), ('res_id', '=', record.id),
                     ('id', 'in', self._new_mails.ids)]))
                self.assertFalse(self.env['mail.message'].sudo().search(
                    [('model', '=', record._name), ('res_id', '=', record.id),
                     ('id', 'in', self._new_mails.mail_message_id.ids)]))

            if check_mail and not mail_not_created:
                if author is None:
                    author = self.env.user.partner_id

                # mail.mail specific values to check
                email_values = recipient_info.get('email_values', {})
                fields_values = {'mailing_id': mailing}
                if recipient_info.get('mail_values'):
                    fields_values.update(recipient_info['mail_values'])
                if 'failure_type' in recipient_info:
                    fields_values['failure_type'] = failure_type
                if 'failure_reason' in recipient_info:
                    fields_values['failure_reason'] = failure_reason
                if 'email_to_mail' in recipient_info:
                    fields_values['email_to'] = recipient_info['email_to_mail']
                if partner:
                    fields_values['recipient_ids'] = partner

                # specific for partner: email_formatted is used
                if partner:
                    if status == 'sent' and sent_unlink:
                        self.assertSentEmail(author, [partner])
                    else:
                        self.assertMailMail(
                            partner, state_mapping[status],
                            author=author,
                            content=content,
                            email_to_recipients=email_to_recipients,
                            fields_values=fields_values,
                            email_values=email_values,
                        )
                # specific if email is False -> could have troubles finding it if several falsy traces
                elif not email and status in ('cancel', 'bounce'):
                    self.assertMailMailWId(
                        recipient_trace.mail_mail_id_int, state_mapping[status],
                        author=author,
                        content=content,
                        email_to_recipients=email_to_recipients,
                        fields_values=fields_values,
                        email_values=email_values,
                    )
                else:
                    self.assertMailMailWEmails(
                        [email_to_mail], state_mapping[status],
                        author=author,
                        content=content,
                        email_to_recipients=email_to_recipients,
                        fields_values=fields_values,
                        email_values=email_values,
                    )

            if link_info and not mail_not_created:
                trace_mail = self._find_mail_mail_wrecord(record)
                for (anchor_id, url, is_shortened, add_link_params) in link_info:
                    link_params = {'utm_medium': 'Email', 'utm_source': mailing.name}
                    if add_link_params:
                        link_params.update(**add_link_params)
                    self.assertLinkShortenedHtml(
                        trace_mail.body_html,
                        (anchor_id, url, is_shortened),
                        link_params=link_params,
                    )

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def gateway_mail_trace_bounce(self, mailing, record, bounce_base_values=None):
        """ Generate a bounce at mailgateway level.

        :param mailing: a ``mailing.mailing`` record on which we find a trace
          to bounce;
        :param record: record which should bounce;
        :param bounce_base_values: optional values given to routing;
        """
        record_email = record[record._primary_email]
        trace = mailing.mailing_trace_ids.filtered(
            lambda t: t.model == record._name and t.res_id == record.id
        )
        self.assertTrue(trace)
        self.assertEqual(trace.email, email_normalize(record_email))

        parsed_bounce_values = {
            'email_from': 'some.email@external.example.com',  # TDE check: email_from -> trace email ?
            'to': 'bounce@test.example.com',  # TDE check: bounce alias ?
            'message_id': mail.generate_tracking_message_id('MailTest'),
            'bounced_partner': self.env['res.partner'].sudo(),
            'bounced_message': self.env['mail.message'].sudo(),
            'body': 'This is the bounce email',
        }
        if bounce_base_values:
            parsed_bounce_values.update(bounce_base_values)
        parsed_bounce_values.update({
            'bounced_email': trace.email,
            'bounced_msg_ids': [trace.message_id],
        })
        self.env['mail.thread']._routing_handle_bounce(False, parsed_bounce_values)
        return trace

    def gateway_mail_trace_click(self, mailing, record, click_label):
        """ Simulate a click on a sent email.

        :param mailing: a ``mailing.mailing`` record on which we find a trace
          to click;
        :param record: record which should click;
        :param click_label: label of link on which we should click;
        """
        record_email = record[record._primary_email]
        trace = mailing.mailing_trace_ids.filtered(
            lambda t: t.model == record._name and t.res_id == record.id
        )
        self.assertTrue(trace)
        self.assertEqual(trace.email, email_normalize(record_email))

        email = self._find_sent_email_wemail(record_email)
        self.assertTrue(bool(email))
        for (_url_href, link_url, _dummy, label) in re.findall(mail.HTML_TAG_URL_REGEX, email['body']):
            if label == click_label and '/r/' in link_url:  # shortened link, like 'http://localhost:8069/r/LBG/m/53'
                parsed_url = werkzeug.urls.url_parse(link_url)
                path_items = parsed_url.path.split('/')
                code, trace_id = path_items[2], int(path_items[4])
                self.assertEqual(trace.id, trace_id)

                self.env['link.tracker.click'].sudo().add_click(
                    code,
                    ip='100.200.300.%3f' % random.random(),
                    country_code='BE',
                    mailing_trace_id=trace.id
                )
                break
        else:
            raise AssertionError('url %s not found in mailing %s for record %s' % (click_label, mailing, record))
        return trace

    def gateway_mail_trace_open(self, mailing, record):
        """ Simulate opening an email through blank.gif icon access. As we
        don't want to use the whole Http layer just for that we will just
        call 'set_opened()' on trace, until having a better option.

        :param mailing: a ``mailing.mailing`` record on which we find a trace
          to open;
        :param record: record which should open;
        """
        trace = mailing.mailing_trace_ids.filtered(
            lambda t: t.model == record._name and t.res_id == record.id
        )
        self.assertTrue(trace)

        trace.set_opened()
        return trace

    def gateway_mail_trace_reply(self, mailing, record):
        """ Simulate replying to an email. As we don't want to use the whole
        mail and gateway layer just for that we will just call 'set_replied()'
        on trace.

        :param mailing: a ``mailing.mailing`` record on which we find a trace
          to open;
        :param record: record which should open;
        """
        trace = mailing.mailing_trace_ids.filtered(
            lambda t: t.model == record._name and t.res_id == record.id
        )
        self.assertTrue(trace)

        trace.set_replied()
        return trace

    @classmethod
    def _create_bounce_trace(cls, mailing, records, dt=None):
        if dt is None:
            dt = datetime.datetime.now() - datetime.timedelta(days=1)
        return cls._create_traces(mailing, records, dt, trace_status='bounce')

    @classmethod
    def _create_sent_traces(cls, mailing, records, dt=None):
        if dt is None:
            dt = datetime.datetime.now() - datetime.timedelta(days=1)
        return cls._create_traces(mailing, records, dt, trace_status='sent')

    @classmethod
    def _create_traces(cls, mailing, records, dt, **values):
        if 'email_normalized' in records:
            fname = 'email_normalized'
        elif 'email_from' in records:
            fname = 'email_from'
        else:
            fname = 'email'
        randomized = random.random()
        # Cursor.now() uses transaction's timestamp and not datetime lib -> freeze_time
        # is not sufficient
        with patch.object(Cursor, 'now', lambda *args, **kwargs: dt):
            traces = cls.env['mailing.trace'].sudo().create([
                dict({'mass_mailing_id': mailing.id,
                      'model': record._name,
                      'res_id': record.id,
                      'trace_status': values.get('trace_status', 'bounce'),
                      # TDE FIXME: improve this with a mail-enabled heuristics
                      'email': record[fname],
                      'message_id': '<%5f@gilbert.boitempomils>' % randomized,
                     }, **values)
                for record in records
            ])
        return traces

    @classmethod
    def _create_mailing_list(cls):
        """ Shortcut to create mailing lists. Currently hardcoded, maybe evolve
        in a near future. """
        cls.mailing_list_1, cls.mailing_list_2, cls.mailing_list_3, cls.mailing_list_4 = cls.env['mailing.list'].with_context(cls._test_context).create([
            {
                'contact_ids': [
                    (0, 0, {'name': 'Déboulonneur', 'email': 'fleurus@example.com'}),
                    (0, 0, {'name': 'Gorramts', 'email': 'gorramts@example.com'}),
                    (0, 0, {'name': 'Ybrant', 'email': 'ybrant@example.com'}),
                ],
                'name': 'List1',
                'is_public': True,
            }, {
                'contact_ids': [
                    (0, 0, {'name': 'Gilberte', 'email': 'gilberte@example.com'}),
                    (0, 0, {'name': 'Gilberte En Mieux', 'email': 'gilberte@example.com'}),
                    (0, 0, {'name': 'Norbert', 'email': 'norbert@example.com'}),
                    (0, 0, {'name': 'Ybrant', 'email': 'ybrant@example.com'}),
                ],
                'name': 'List2',
                'is_public': True,
            }, {
                'contact_ids': [
                    (0, 0, {'name': 'Déboulonneur', 'email': 'fleurus@example.com'}),
                ],
                'name': 'List3',
                'is_public': True,
            }, {
                'name': 'List4',
            }
        ])
        cls.mailing_list_3.subscription_ids[0].opt_out = True

    @classmethod
    def _create_mailing_list_of_x_contacts(cls, contacts_nbr):
        """ Shortcut to create a mailing list that contains a defined number
        of contacts. """
        return cls.env['mailing.list'].with_context(cls._test_context).create({
            'name': 'Test List',
            'contact_ids': [
                (0, 0, {
                    'name': f'Contact %{idx}',
                    'email': f'contact%{idx}@example.com'
                })
                for idx in range(contacts_nbr)
            ],
        })


class MassMailCommon(MailCommon, MassMailCase):

    @classmethod
    def setUpClass(cls):
        super(MassMailCommon, cls).setUpClass()

        cls.user_marketing, cls.user_marketing_1 = [mail_new_test_user(
            cls.env,
            groups='base.group_user,base.group_partner_manager,mass_mailing.group_mass_mailing_user',
            login=f'user_marketing{suffix}',
            name=f'Martial Marketing{suffix}',
            signature=f'--\nMartial{suffix}',
        ) for suffix in ('', '_1')]

        cls.email_reply_to = 'MyCompany SomehowAlias <test.alias@test.mycompany.com>'

        cls.env.flush_all()
