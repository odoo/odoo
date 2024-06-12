# -*- coding: utf-8 -*-

from contextlib import contextmanager
from unittest.mock import patch

from odoo import exceptions, tools
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.sms.models.sms_sms import SmsApi, SmsSms
from odoo.tests import common


class MockSMS(common.BaseCase):

    def tearDown(self):
        super(MockSMS, self).tearDown()
        self._clear_sms_sent()

    @contextmanager
    def mockSMSGateway(self, sms_allow_unlink=False, sim_error=None, nbr_t_error=None, moderated=False):
        self._clear_sms_sent()
        sms_create_origin = SmsSms.create
        sms_send_origin = SmsSms._send

        def _contact_iap(local_endpoint, params):
            # mock single sms sending
            if local_endpoint == '/iap/message_send':
                self._sms += [{
                    'number': number,
                    'body': params['message'],
                } for number in params['numbers']]
                return True  # send_message v0 API returns always True
            # mock batch sending
            if local_endpoint == '/iap/sms/2/send':
                result = []
                for to_send in params['messages']:
                    res = {'res_id': to_send['res_id'], 'state': 'success', 'credit': 1}
                    error = sim_error or (nbr_t_error and nbr_t_error.get(to_send['number']))
                    if error and error == 'credit':
                        res.update(credit=0, state='insufficient_credit')
                    elif error and error in {'wrong_number_format', 'unregistered', 'server_error'}:
                        res.update(state=error)
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
            elif local_endpoint == '/api/sms/3/send':
                result = []
                for message in params['messages']:
                    for number in message["numbers"]:
                        error = sim_error or (nbr_t_error and nbr_t_error.get(number['number']))
                        if error == 'jsonrpc_exception':
                            raise exceptions.AccessError(
                                'The url that this service requested returned an error. '
                                'Please contact the author of the app. '
                                'The url it tried to contact was ' + local_endpoint
                            )
                        elif error == 'credit':
                            error = 'insufficient_credit'
                        res = {
                            'uuid': number['uuid'],
                            'state': error if error else 'success' if not moderated else 'processing',
                            'credit': 1,
                        }
                        if error:
                            # credit is only given if the amount is known
                            res.update(credit=0)
                        else:
                            self._sms.append({
                                'number': number['number'],
                                'body': message['content'],
                                'uuid': number['uuid'],
                            })
                        result.append(res)
                return result

        def _sms_sms_create(model, *args, **kwargs):
            res = sms_create_origin(model, *args, **kwargs)
            self._new_sms += res.sudo()
            return res

        def _sms_sms_send(records, unlink_failed=False, unlink_sent=True, raise_exception=False):
            if sms_allow_unlink:
                return sms_send_origin(records, unlink_failed=unlink_failed, unlink_sent=unlink_sent, raise_exception=raise_exception)
            return sms_send_origin(records, unlink_failed=False, unlink_sent=False, raise_exception=raise_exception)

        try:
            with patch.object(SmsApi, '_contact_iap', side_effect=_contact_iap), \
                    patch.object(SmsSms, 'create', autospec=True, wraps=SmsSms, side_effect=_sms_sms_create), \
                    patch.object(SmsSms, '_send', autospec=True, wraps=SmsSms, side_effect=_sms_sms_send):
                yield
        finally:
            pass

    def _clear_sms_sent(self):
        self._sms = []
        self._new_sms = self.env['sms.sms'].sudo()

    def _clear_outgoing_sms(self):
        """ As SMS gateway mock keeps SMS, we may need to remove them manually
        if there are several tests in the same tx. """
        self.env['sms.sms'].sudo().search([('state', '=', 'outgoing')]).unlink()


class SMSCase(MockSMS):
    """ Main test class to use when testing SMS integrations. Contains helpers and tools related
    to notification sent by SMS. """

    def _find_sms_sent(self, partner, number):
        if number is None and partner:
            number = partner._phone_format()
        sent_sms = next((sms for sms in self._sms if sms['number'] == number), None)
        if not sent_sms:
            raise AssertionError('sent sms not found for %s (number: %s)' % (partner, number))
        return sent_sms

    def _find_sms_sms(self, partner, number, status):
        if number is None and partner:
            number = partner._phone_format()
        domain = [('id', 'in', self._new_sms.ids),
                  ('partner_id', '=', partner.id),
                  ('number', '=', number)]
        if status:
            domain += [('state', '=', status)]

        sms = self.env['sms.sms'].sudo().search(domain)
        if not sms:
            raise AssertionError('sms.sms not found for %s (number: %s / status %s)' % (partner, number, status))
        if len(sms) > 1:
            raise NotImplementedError()
        return sms

    def assertSMSIapSent(self, numbers, content=None):
        """ Check sent SMS. Order is not checked. Each number should have received
        the same content. Useful to check batch sending.

        :param numbers: list of numbers;
        :param content: content to check for each number;
        """
        for number in numbers:
            sent_sms = next((sms for sms in self._sms if sms['number'] == number), None)
            self.assertTrue(bool(sent_sms), 'Number %s not found in %s' % (number, repr([s['number'] for s in self._sms])))
            if content is not None:
                self.assertIn(content, sent_sms['body'])

    def assertSMS(self, partner, number, status, failure_type=None,
                  content=None, fields_values=None):
        """ Find a ``sms.sms`` record, based on given partner, number and status.

        :param partner: optional partner, used to find a ``sms.sms`` and a number
          if not given;
        :param number: optional number, used to find a ``sms.sms``, notably if
          partner is not given;
        :param failure_type: check failure type if SMS is not sent or outgoing;
        :param content: if given, should be contained in sms body;
        :param fields_values: optional values allowing to check directly some
          values on ``sms.sms`` record;
        """
        sms_sms = self._find_sms_sms(partner, number, status)
        if failure_type:
            self.assertEqual(sms_sms.failure_type, failure_type)
        if content is not None:
            self.assertIn(content, sms_sms.body)
        for fname, fvalue in (fields_values or {}).items():
            self.assertEqual(
                sms_sms[fname], fvalue,
                'SMS: expected %s for %s, got %s' % (fvalue, fname, sms_sms[fname]))
        if status == 'pending':
            self.assertSMSIapSent([sms_sms.number], content=content)

    def assertSMSCanceled(self, partner, number, failure_type, content=None, fields_values=None):
        """ Check canceled SMS. Search is done for a pair partner / number where
        partner can be an empty recordset. """
        self.assertSMS(partner, number, 'canceled', failure_type=failure_type, content=content, fields_values=fields_values)

    def assertSMSFailed(self, partner, number, failure_type, content=None, fields_values=None):
        """ Check failed SMS. Search is done for a pair partner / number where
        partner can be an empty recordset. """
        self.assertSMS(partner, number, 'error', failure_type=failure_type, content=content, fields_values=fields_values)

    def assertSMSOutgoing(self, partner, number, content=None, fields_values=None):
        """ Check outgoing SMS. Search is done for a pair partner / number where
        partner can be an empty recordset. """
        self.assertSMS(partner, number, 'outgoing', content=content, fields_values=fields_values)

    def assertNoSMSNotification(self, messages=None):
        base_domain = [('notification_type', '=', 'sms')]
        if messages is not None:
            base_domain += [('mail_message_id', 'in', messages.ids)]
        self.assertEqual(self.env['mail.notification'].search(base_domain), self.env['mail.notification'])
        self.assertEqual(self._sms, [])

    def assertSMSNotification(self, recipients_info, content, messages=None, check_sms=True, sent_unlink=False):
        """ Check content of notifications.

          :param recipients_info: list[{
            'partner': res.partner record (may be empty),
            'number': number used for notification (may be empty, computed based on partner),
            'state': ready / pending / sent / exception / canceled (pending by default),
            'failure_type': optional: sms_number_missing / sms_number_format / sms_credit / sms_server
            }, { ... }]
        """
        partners = self.env['res.partner'].concat(*list(p['partner'] for p in recipients_info if p.get('partner')))
        numbers = [p['number'] for p in recipients_info if p.get('number')]
        # special case of void notifications: check for False / False notifications
        if not partners and not numbers:
            numbers = [False]
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
            state = recipient_info.get('state', 'pending')
            if number is None and partner:
                number = partner._phone_format()

            notif = notifications.filtered(lambda n: n.res_partner_id == partner and n.sms_number == number and n.notification_status == state)

            debug_info = ''
            if not notif:
                debug_info = '\n'.join(
                    f'To: {notif.sms_number} ({notif.res_partner_id}) - (State: {notif.notification_status})'
                    for notif in notifications
                )
            self.assertTrue(notif, 'SMS: not found notification for %s (number: %s, state: %s)\n%s' % (partner, number, state, debug_info))
            self.assertEqual(notif.author_id, notif.mail_message_id.author_id, 'SMS: Message and notification should have the same author')

            if state not in {'process', 'sent', 'ready', 'canceled', 'pending'}:
                self.assertEqual(notif.failure_type, recipient_info['failure_type'])
            if check_sms:
                if state in {'process', 'pending', 'sent'}:
                    if sent_unlink:
                        self.assertSMSIapSent([number], content=content)
                    else:
                        self.assertSMS(partner, number, state, content=content)
                elif state == 'ready':
                    self.assertSMS(partner, number, 'outgoing', content=content)
                elif state == 'exception':
                    self.assertSMS(partner, number, 'error', failure_type=recipient_info['failure_type'], content=content)
                elif state == 'canceled':
                    self.assertSMS(partner, number, 'canceled', failure_type=recipient_info['failure_type'], content=content)
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


class SMSCommon(MailCommon, SMSCase):

    @classmethod
    def setUpClass(cls):
        super(SMSCommon, cls).setUpClass()
        cls.user_employee.write({'login': 'employee'})

        # update country to belgium in order to test sanitization of numbers
        cls.user_employee.company_id.write({'country_id': cls.env.ref('base.be').id})

        # some numbers for testing
        cls.random_numbers_str = '+32456998877, 0456665544'
        cls.random_numbers = cls.random_numbers_str.split(', ')
        cls.random_numbers_san = [phone_validation.phone_format(number, 'BE', '32', force_format='E164') for number in cls.random_numbers]
        cls.test_numbers = ['+32456010203', '0456 04 05 06', '0032456070809']
        cls.test_numbers_san = [phone_validation.phone_format(number, 'BE', '32', force_format='E164') for number in cls.test_numbers]

        # some numbers for mass testing
        cls.mass_numbers = ['04561%s2%s3%s' % (x, x, x) for x in range(0, 10)]
        cls.mass_numbers_san = [phone_validation.phone_format(number, 'BE', '32', force_format='E164') for number in cls.mass_numbers]

    @classmethod
    def _create_sms_template(cls, model, body=False):
        return cls.env['sms.template'].create({
            'name': 'Test Template',
            'model_id': cls.env['ir.model']._get(model).id,
            'body': body if body else 'Dear {{ object.display_name }} this is an SMS.'
        })

    def _make_webhook_jsonrpc_request(self, statuses):
        return self.make_jsonrpc_request('/sms/status', {'message_statuses': statuses})
