# -*- coding: utf-8 -*-

import re
import werkzeug

from odoo import tools
from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.addons.sms.tests.common import SMSCase, SMSCommon


class MassSMSCase(SMSCase):

    # ------------------------------------------------------------
    # GATEWAY TOOLS
    # ------------------------------------------------------------

    def gateway_sms_click(self, sent_sms):
        """ Simulate a click on a sent SMS. Usage: giving a partner and/or
        a number, find an SMS sent to him, find shortened links in its body
        and call add_click to simulate a click. """
        for url in re.findall(tools.TEXT_URL_REGEX, sent_sms['body']):
            if '/r/' in url:  # shortened link, like 'http://localhost:8069/r/LBG/s/53'
                parsed_url = werkzeug.urls.url_parse(url)
                path_items = parsed_url.path.split('/')
                code, sms_sms_id = path_items[2], int(path_items[4])
                trace_id = self.env['mailing.trace'].sudo().search([('sms_sms_id_int', '=', sms_sms_id)]).id

                self.env['link.tracker.click'].sudo().add_click(
                    code,
                    ip='100.200.300.400',
                    country_code='BE',
                    mailing_trace_id=trace_id
                )


    # ------------------------------------------------------------
    # ASSERTS
    # ------------------------------------------------------------

    def assertSMSOutgoingStatistics(self, partners, numbers, records, mailing):
        found_sms = self.env['sms.sms'].sudo().search([
            '|', ('partner_id', 'in', partners.ids), ('number', 'in', numbers),
            ('state', '=', 'outgoing')
        ])
        self.assertEqual(found_sms.filtered(lambda s: s.partner_id).mapped('partner_id'), partners)
        self.assertEqual(set(found_sms.filtered(lambda s: not s.partner_id).mapped('number')), set(numbers))

        found_traces = self.env['mailing.trace'].sudo().search([
            ('sms_sms_id_int', 'in', found_sms.ids),
        ])
        self.assertEqual(len(found_sms), len(found_traces))
        self.assertTrue(all(s.state == 'outgoing' for s in found_traces))
        self.assertTrue(all(s.res_model == records._name for s in found_traces))
        self.assertEqual(set(found_traces.mapped('res_id')), set(records.ids))
        self.assertTrue(all(s.mass_mailing_id == mailing for s in found_traces))

    def assertSMSStatistics(self, recipients_info, mailing, records, check_sms=True):
        """ Check content of notifications.

        :param recipients_info: list[{
          'partner': res.partner record (may be empty),
          'number': number used for notification (may be empty, computed based on partner),
          'state': outgoing / sent / ignored / exception / opened (sent by default),
          'record: linked record,
          'content': optional: if set, check content of sent SMS
          'failure_type': optional: sms_number_missing / sms_number_format / sms_credit / sms_server
          },
          { ... }
        ]
        """
        traces = self.env['mailing.trace'].search([
            ('mass_mailing_id', 'in', mailing.ids),
            ('res_id', 'in', records.ids)
        ])

        self.assertTrue(all(s.model == records._name for s in traces))
        # self.assertTrue(all(s.utm_campaign_id == mailing.campaign_id for s in traces))
        self.assertEqual(set(s.res_id for s in traces), set(records.ids))

        for recipient_info in recipients_info:
            partner = recipient_info.get('partner', self.env['res.partner'])
            number = recipient_info.get('number')
            state = recipient_info.get('state', 'outgoing')
            content = recipient_info.get('content', None)
            if number is None and partner:
                number = partner._sms_get_recipients_info()[partner.id]['sanitized']

            notif = traces.filtered(lambda s: s.sms_number == number and s.state == state)
            self.assertTrue(notif, 'SMS: not found notification for number %s, (state: %s)' % (number, state))

            if check_sms:
                if state == 'sent':
                    self.assertSMSSent([number], content)
                elif state == 'outgoing':
                    self.assertSMSOutgoing(partner, number, content)
                elif state == 'exception':
                    self.assertSMSFailed(partner, number, recipient_info.get('failure_type'), content)
                elif state == 'ignored':
                    self.assertSMSCanceled(partner, number, recipient_info.get('failure_type', False), content)
                else:
                    raise NotImplementedError()


class MassSMSCommon(MassMailCommon, SMSCommon, MassSMSCase):

    @classmethod
    def setUpClass(cls):
        super(MassSMSCommon, cls).setUpClass()
