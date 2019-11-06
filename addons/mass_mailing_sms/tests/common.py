# -*- coding: utf-8 -*-

from contextlib import contextmanager
from unittest.mock import patch

from odoo import exceptions, tools
from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.sms.tests import common as sms_common
from odoo.tests import common
from odoo.addons.sms.models.sms_api import SmsApi


class MockSMS(sms_common.MockSMS):

    def assertSMSOutgoingStatistics(self, partners, numbers, records, mailing):
        found_sms = self.env['sms.sms'].sudo().search([
            '|', ('partner_id', 'in', partners.ids), ('number', 'in', numbers),
            ('state', '=', 'outgoing')
        ])
        self.assertEqual(found_sms.filtered(lambda s: s.partner_id).mapped('partner_id'), partners)
        self.assertEqual(set(found_sms.filtered(lambda s: not s.partner_id).mapped('number')), set(numbers))

        found_traces = self.env['mailing.trace'].sudo().search([
            ('sms_id_int', 'in', found_sms.ids),
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
            'state': outgoing / sent / canceled / exception / opened (sent by default),
            'record: linked record,
            'failure_type': optional: sms_number_missing / sms_number_format / sms_credit / sms_server
            }, { ... }]
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
                number = phone_validation.phone_get_sanitized_record_number(partner)

            notif = traces.filtered(lambda s: s.sms_number == number and s.state == state)
            self.assertTrue(notif, 'SMS: not found notification for number %s, (state: %s)' % (number, state))

            if check_sms:
                if state == 'sent':
                    self.assertSMSSent([number], content)
                elif state == 'outgoing':
                    self.assertSMSOutgoing(partner, number, content)
                elif state == 'exception':
                    self.assertSMSFailed(partner, number, recipient_info.get('failure_type'), content)
                elif state == 'canceled':
                    self.assertSMSCanceled(partner, number, recipient_info.get('failure_type', False), content)
                else:
                    raise NotImplementedError()
