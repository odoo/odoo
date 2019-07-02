# -*- coding: utf-8 -*-

from contextlib import contextmanager
from unittest.mock import patch

from odoo import exceptions
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
                    elif error and error == 'wrong_format_number':
                        res.update(state='wrong_format_number')
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

    def assertSMSSent(self, numbers, content):
        """ Check sent SMS. Order is not checked. Each number should have received
        the same content. Usefull to check batch sending.

        :param numbers: list of numbers;
        :param content: content to check for each number;
        """
        self.assertEqual(len(self._sms), len(numbers))
        for number in numbers:
            sent_sms = next((sms for sms in self._sms if sms['number'] == number), None)
            self.assertTrue(bool(sent_sms), 'Number %s not found in %s' % (number, repr([s['number'] for s in self._sms])))
            self.assertEqual(sent_sms['body'], content)

    def _clear_sms_sent(self):
        self._sms = []
