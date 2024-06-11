# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from unittest.mock import DEFAULT

from odoo import exceptions
from odoo.addons.link_tracker.tests.common import MockLinkTracker
from odoo.addons.sms.models.sms_sms import SmsSms as SmsModel
from odoo.addons.sms.tests.common import SMSCommon
from odoo.tests import tagged


@tagged('link_tracker')
class TestSMSPost(SMSCommon, MockLinkTracker):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._test_body = 'VOID CONTENT'

        cls.sms_all = cls.env['sms.sms']
        for x in range(10):
            cls.sms_all |= cls.env['sms.sms'].create({
                'number': '+324560000%s%s' % (x, x),
                'body': cls._test_body,
            })

    def test_sms_send_batch_size(self):
        self.count = 0

        def _send(sms_self, unlink_failed=False, unlink_sent=True, raise_exception=False):
            self.count += 1
            return DEFAULT

        self.env['ir.config_parameter'].set_param('sms.session.batch.size', '3')
        with patch.object(SmsModel, '_send', autospec=True, side_effect=_send) as _send_mock:
            self.env['sms.sms'].browse(self.sms_all.ids).send()

        self.assertEqual(self.count, 4)

    def test_sms_send_crash_employee(self):
        with self.assertRaises(exceptions.AccessError):
            self.env['sms.sms'].with_user(self.user_employee).browse(self.sms_all.ids).send()

    def test_sms_send_delete_all(self):
        with self.mockSMSGateway(sms_allow_unlink=True, sim_error='jsonrpc_exception'):
            self.env['sms.sms'].browse(self.sms_all.ids).send(unlink_failed=True, unlink_sent=True, raise_exception=False)
        self.assertFalse(len(self.sms_all.exists().filtered(lambda s: not s.to_delete)))

    def test_sms_send_delete_default(self):
        """ Test default send behavior: keep failed SMS, remove sent. """
        with self.mockSMSGateway(sms_allow_unlink=True, nbr_t_error={
                '+32456000011': 'wrong_number_format',
                '+32456000022': 'credit',
                '+32456000033': 'server_error',
                '+32456000044': 'unregistered',
        }):
            self.env['sms.sms'].browse(self.sms_all.ids).send(raise_exception=False)
        remaining = self.sms_all.exists().filtered(lambda s: not s.to_delete)
        self.assertEqual(len(remaining), 4)
        self.assertEqual(set(remaining.mapped('state')), {'error'})

    def test_sms_send_delete_failed(self):
        with self.mockSMSGateway(sms_allow_unlink=True, nbr_t_error={
                '+32456000011': 'wrong_number_format',
                '+32456000022': 'wrong_number_format',
        }):
            self.env['sms.sms'].browse(self.sms_all.ids).send(unlink_failed=True, unlink_sent=False, raise_exception=False)
        remaining = self.sms_all.exists().filtered(lambda s: not s.to_delete)
        self.assertEqual(len(remaining), 8)
        self.assertEqual(set(remaining.mapped('state')), {'pending'})

    def test_sms_send_delete_none(self):
        with self.mockSMSGateway(sms_allow_unlink=True, nbr_t_error={
                '+32456000011': 'wrong_number_format',
                '+32456000022': 'wrong_number_format',
        }):
            self.env['sms.sms'].browse(self.sms_all.ids).send(unlink_failed=False, unlink_sent=False, raise_exception=False)
        self.assertEqual(len(self.sms_all.exists()), 10)
        success_sms = self.sms_all[:1] + self.sms_all[3:]
        error_sms = self.sms_all[1:3]
        self.assertEqual(set(success_sms.mapped('state')), {'pending'})
        self.assertEqual(set(error_sms.mapped('state')), {'error'})

    def test_sms_send_delete_sent(self):
        with self.mockSMSGateway(sms_allow_unlink=True, nbr_t_error={
                '+32456000011': 'wrong_number_format',
                '+32456000022': 'wrong_number_format',
        }):
            self.env['sms.sms'].browse(self.sms_all.ids).send(unlink_failed=False, unlink_sent=True, raise_exception=False)
        remaining = self.sms_all.exists().filtered(lambda s: not s.to_delete)
        self.assertEqual(len(remaining), 2)
        self.assertEqual(set(remaining.mapped('state')), {'error'})

    def test_sms_send_raise(self):
        with self.assertRaises(exceptions.AccessError):
            with self.mockSMSGateway(sim_error='jsonrpc_exception'):
                self.env['sms.sms'].browse(self.sms_all.ids).send(raise_exception=True)
        self.assertEqual(set(self.sms_all.mapped('state')), {'outgoing'})

    def test_sms_send_raise_catch(self):
        with self.mockSMSGateway(sim_error='jsonrpc_exception'):
            self.env['sms.sms'].browse(self.sms_all.ids).send(raise_exception=False)
        self.assertEqual(set(self.sms_all.mapped('state')), {'error'})

    def test_sms_send_to_process(self):
        with self.mockSMSGateway(moderated=True):
            self.env['sms.sms'].browse(self.sms_all.ids).send(raise_exception=False)
        self.assertEqual(set(self.sms_all.mapped('state')), {'process'})

    def test_sms_send_to_unknown_error(self):
        with self.mockSMSGateway(sim_error='something_new'):
            self.env['sms.sms'].browse(self.sms_all.ids).send()
        self.assertEqual(set(self.sms_all.mapped('state')), {'error'})
