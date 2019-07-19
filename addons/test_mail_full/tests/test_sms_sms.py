# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from unittest.mock import DEFAULT

from odoo import exceptions
from odoo.addons.sms.models.sms_sms import SmsSms as SmsSms
from odoo.addons.sms.tests import common as sms_common
from odoo.addons.test_mail_full.tests import common as test_mail_full_common


class TestSMSPost(test_mail_full_common.BaseFunctionalTest, sms_common.MockSMS):

    @classmethod
    def setUpClass(cls):
        super(TestSMSPost, cls).setUpClass()
        cls._test_body = 'VOID CONTENT'

        cls.sms_all = cls.env['sms.sms']
        for x in range(10):
            cls.sms_all |= cls.env['sms.sms'].create({
                'number': '+324560000%s%s' % (x, x),
                'body': cls._test_body,
            })

    def test_sms_send_batch_size(self):
        self.count = 0

        def _send(sms_self, delete_all=False, raise_exception=False):
            self.count += 1
            return DEFAULT

        self.env['ir.config_parameter'].set_param('sms.session.batch.size', '3')
        with patch.object(SmsSms, '_send', autospec=True, side_effect=_send) as send_mock:
            self.env['sms.sms'].browse(self.sms_all.ids).send()

        self.assertEqual(self.count, 4)

    def test_sms_send_crash_employee(self):
        with self.assertRaises(exceptions.AccessError):
            self.env['sms.sms'].with_user(self.user_employee).browse(self.sms_all.ids).send()

    def test_sms_send_delete_all(self):
        with self.mockSMSGateway(sim_error='jsonrpc_exception'):
            self.env['sms.sms'].browse(self.sms_all.ids).send(delete_all=True, raise_exception=False)
        self.assertFalse(len(self.sms_all.exists()))

    def test_sms_send_raise(self):
        with self.assertRaises(exceptions.AccessError):
            with self.mockSMSGateway(sim_error='jsonrpc_exception'):
                self.env['sms.sms'].browse(self.sms_all.ids).send(raise_exception=True)
        self.assertEqual(set(self.sms_all.mapped('state')), set(['outgoing']))

    def test_sms_send_raise_catch(self):
        with self.mockSMSGateway(sim_error='jsonrpc_exception'):
            self.env['sms.sms'].browse(self.sms_all.ids).send(raise_exception=False)
        self.assertEqual(set(self.sms_all.mapped('state')), set(['error']))
