# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
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
        cls.now = datetime(2025, 12, 1, 10, 0, 0)
        cls.env['ir.config_parameter'].sudo().set_int("mass_mailing.cancelled_mails_months_limit", 6)

        cls.sms_all = cls.env['sms.sms']
        with cls.mock_datetime_and_now(cls, cls.now):
            for x in range(10):
                cls.sms_all |= cls.env['sms.sms'].create({
                    'number': '+324560000%s%s' % (x, x),
                    'body': cls._test_body,
                })

    def test_sms_send_batch_size(self):
        self.count = 0

        def _send(sms_self, unlink_sent=True, raise_exception=False):
            self.count += 1
            return DEFAULT

        self.env['ir.config_parameter'].set_int('sms.session.batch.size', 3)
        with patch.object(SmsModel, '_send', autospec=True, side_effect=_send) as _send_mock:
            self.env['sms.sms'].browse(self.sms_all.ids).send()

        self.assertEqual(self.count, 4)

    def test_sms_send_crash_employee(self):
        with self.assertRaises(exceptions.AccessError):
            self.env['sms.sms'].with_user(self.user_employee).browse(self.sms_all.ids).send()

    def test_sms_send_delete_all(self):
        """ With unlink option activated, all SMS are marked as to_delete, even
        those in error. Cron will garbage collect them after 6 months. """
        with self.mock_datetime_and_now(self.now + relativedelta(months=1)), \
             self.mockSMSGateway(sms_allow_unlink=True, sim_error='jsonrpc_exception'):
            self.env['sms.sms'].browse(self.sms_all.ids).send(unlink_sent=True, raise_exception=False)
        remaining = self.sms_all.exists()
        self.assertEqual(remaining, self.sms_all)
        self.assertFalse(remaining.filtered(lambda s: not s.to_delete), 'Should mark as to_delete, as asked')
        self.assertEqual(set(remaining.mapped('to_delete')), {True},
            'Should all be marked as "to_delete", even if all failed'
        )
        self.assertEqual(self.sms_all.mapped('state'), ['error'] * len(self.sms_all))

        # inside "keep timeframe"
        with self.mock_datetime_and_now(self.now + relativedelta(months=6)):
            self.env['sms.sms']._gc_old_sms()
        self.assertEqual(
            self.sms_all.exists(), self.sms_all,
            'Should not be GC, not 6 months after last update'
        )

        # out of "keep timeframe"
        with self.mock_datetime_and_now(self.now + relativedelta(months=7)):
            self.env['sms.sms']._gc_old_sms()
        self.assertFalse(self.sms_all.exists(), 'Should be GC, 6 months after last update')

    def test_sms_send_delete_default(self):
        """ Test default send behavior: mark all as to_delete """
        with self.mockSMSGateway(sms_allow_unlink=True, nbr_t_error={
                '+32456000011': 'wrong_number_format',
                '+32456000022': 'credit',
                '+32456000033': 'server_error',
                '+32456000044': 'unregistered',
        }):
            self.env['sms.sms'].browse(self.sms_all.ids).send(raise_exception=False)
        remaining = self.sms_all.exists()
        self.assertEqual(remaining, self.sms_all)
        self.assertFalse(remaining.filtered(lambda s: not s.to_delete), 'Should mark as to_delete by default')
        self.assertEqual(set(remaining.mapped('to_delete')), {True},
            'Should all be marked as "to_delete", even if all failed'
        )

    def test_sms_send_delete_none(self):
        with self.mockSMSGateway(sms_allow_unlink=True, nbr_t_error={
                '+32456000011': 'wrong_number_format',
                '+32456000022': 'wrong_number_format',
        }):
            self.env['sms.sms'].browse(self.sms_all.ids).send(unlink_sent=False, raise_exception=False)
        remaining = self.sms_all.exists()
        self.assertEqual(remaining, self.sms_all)
        success_sms = self.sms_all[:1] + self.sms_all[3:]
        error_sms = self.sms_all[1:3]
        self.assertEqual(set(success_sms.mapped('state')), {'pending'})
        self.assertEqual(set(error_sms.mapped('state')), {'error'})
        self.assertEqual(set(remaining.mapped('to_delete')), {False}, 'All should be set as to keep')

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
