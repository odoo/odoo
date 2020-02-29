# -*- coding: utf-8 -*-

from contextlib import contextmanager
from unittest.mock import patch

from odoo import exceptions, tools
from odoo.addons.phone_validation.tools import phone_validation
from odoo.tests import common
from odoo.addons.sms.models.sms_api import SmsApi


class MockSMS(common.BaseCase):

    def tearDown(self):
        super(MockSMS, self).tearDown()
        self._clear_sms_sent

    @contextmanager
    def mockSMSGateway(self, sim_error=None, nbr_t_error=None):
        self._sms = []

        def _contact_iap(local_endpoint, params):
            # mock single sms sending
            if local_endpoint == '/iap/message_send':
                self._sms += [{
                    'number': number,
                    'body': params['message'],
                } for number in params['numbers']]
                return True  # send_message v0 API returns always True
            # mock batch sending
            if local_endpoint == '/iap/sms/1/send':
                result = []
                for to_send in params['messages']:
                    res = {'res_id': to_send['res_id'], 'state': 'success', 'credit': 1}
                    error = sim_error or (nbr_t_error and nbr_t_error.get(to_send['number']))
                    if error and error == 'credit':
                        res.update(credit=0, state='insufficient_credit')
                    elif error and error == 'wrong_number_format':
                        res.update(state='wrong_number_format')
                    elif error and error == 'jsonrpc_exception':
                        raise exceptions.AccessError(
                            'The url that this service requested returned an error. Please contact the author of the app. The url it tried to contact was ' + local_endpoint
                        )
                    result.append(res)
                    if res['state'] == 'success':
                        self._sms.append({
                            'number': to_send['number'],
                            'body': to_send['content'],
                        })
                return result

        try:
            with patch.object(SmsApi, '_contact_iap', side_effect=_contact_iap) as contact_iap_mock:
                yield
        finally:
            pass

    def _clear_sms_sent(self):
        self._sms = []

    def assertSMSSent(self, numbers, content):
        """ Check sent SMS. Order is not checked. Each number should have received
        the same content. Useful to check batch sending.

        :param numbers: list of numbers;
        :param content: content to check for each number;
        """
        for number in numbers:
            sent_sms = next((sms for sms in self._sms if sms['number'] == number), None)
            self.assertTrue(bool(sent_sms), 'Number %s not found in %s' % (number, repr([s['number'] for s in self._sms])))
            self.assertEqual(sent_sms['body'], content)

    def assertSMSCanceled(self, partner, number, error_code, content=None):
        """ Check canceled SMS. Search is done for a pair partner / number where
        partner can be an empty recordset. """
        if number is None and partner:
            number = partner.phone_get_sanitized_number()
        sms = self.env['sms.sms'].sudo().search([
            ('partner_id', '=', partner.id), ('number', '=', number),
            ('state', '=', 'canceled')
        ])
        self.assertTrue(sms, 'SMS: not found canceled SMS for %s (number: %s)' % (partner, number))
        self.assertEqual(sms.error_code, error_code)
        if content is not None:
            self.assertEqual(sms.body, content)

    def assertSMSFailed(self, partner, number, error_code, content=None):
        """ Check failed SMS. Search is done for a pair partner / number where
        partner can be an empty recordset. """
        if number is None and partner:
            number = partner.phone_get_sanitized_number()
        sms = self.env['sms.sms'].sudo().search([
            ('partner_id', '=', partner.id), ('number', '=', number),
            ('state', '=', 'error')
        ])
        self.assertTrue(sms, 'SMS: not found failed SMS for %s (number: %s)' % (partner, number))
        self.assertEqual(sms.error_code, error_code)
        if content is not None:
            self.assertEqual(sms.body, content)

    def assertSMSOutgoing(self, partner, number, content=None):
        """ Check outgoing SMS. Search is done for a pair partner / number where
        partner can be an empty recordset. """
        if number is None and partner:
            number = partner.phone_get_sanitized_number()
        sms = self.env['sms.sms'].sudo().search([
            ('partner_id', '=', partner.id), ('number', '=', number),
            ('state', '=', 'outgoing')
        ])
        self.assertTrue(sms, 'SMS: not found failed SMS for %s (number: %s)' % (partner, number))
        if content is not None:
            self.assertEqual(sms.body, content)

    def assertSMSNotification(self, recipients_info, content, messages=None, check_sms=True):
        """ Check content of notifications.

          :param recipients_info: list[{
            'partner': res.partner record (may be empty),
            'number': number used for notification (may be empty, computed based on partner),
            'state': ready / sent / exception / canceled (sent by default),
            'failure_type': optional: sms_number_missing / sms_number_format / sms_credit / sms_server
            }, { ... }]
        """
        partners = self.env['res.partner'].concat(*list(p['partner'] for p in recipients_info if p.get('partner')))
        numbers = [p['number'] for p in recipients_info if p.get('number')]
        base_domain = [
            '|', ('res_partner_id', 'in', partners.ids),
            '&', ('res_partner_id', '=', False), ('sms_number', 'in', numbers),
            ('notification_type', '=', 'sms')
        ]
        if messages is not None:
            base_domain += [('mail_message_id', 'in', messages.ids)]
        notifications = self.env['mail.notification'].search(base_domain)

        self.assertEqual(notifications.mapped('res_partner_id'), partners)

        for recipient_info in recipients_info:
            partner = recipient_info.get('partner', self.env['res.partner'])
            number = recipient_info.get('number')
            state = recipient_info.get('state', 'sent')
            if number is None and partner:
                number = partner.phone_get_sanitized_number()

            notif = notifications.filtered(lambda n: n.res_partner_id == partner and n.sms_number == number and n.notification_status == state)
            self.assertTrue(notif, 'SMS: not found notification for %s (number: %s, state: %s)' % (partner, number, state))

            if state not in ('sent', 'ready', 'canceled'):
                self.assertEqual(notif.failure_type, recipient_info['failure_type'])
            if check_sms:
                if state == 'sent':
                    self.assertSMSSent([number], content)
                elif state == 'ready':
                    self.assertSMSOutgoing(partner, number, content)
                elif state == 'exception':
                    self.assertSMSFailed(partner, number, recipient_info['failure_type'], content)
                elif state == 'canceled':
                    self.assertSMSCanceled(partner, number, recipient_info.get('failure_type', False), content)
                else:
                    raise NotImplementedError('Not implemented')

        if messages is not None:
            for message in messages:
                self.assertEqual(content, tools.html2plaintext(message.body).rstrip('\n'))

    def assertSMSLogged(self, records, body):
        for record in records:
            message = record.message_ids[-1]
            self.assertEqual(message.subtype_id, self.env.ref('mail.mt_note'))
            self.assertEqual(message.message_type, 'sms')
            self.assertEqual(tools.html2plaintext(message.body).rstrip('\n'), body)
