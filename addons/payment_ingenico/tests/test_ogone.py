# -*- coding: utf-8 -*-

import time

from odoo.addons.payment.tests.common import PaymentAcquirerCommon

import odoo.tests
from odoo.tools import mute_logger
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'external', '-standard')
class OgonePayment(PaymentAcquirerCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.ogone = cls.env.ref('payment.payment_acquirer_ingenico')
        cls.ogone.write({
            'ogone_pspid': 'pinky',
            'ogone_userid': 'OOAPI',
            'ogone_password': 'R!ci/6Nu8a',
            'ogone_shakey_in': 'tINY4Yv14789gUix1130',
            'ogone_shakey_out': 'tINYj885Tfvd4P471464',
            'state': 'test',
        })
        cls.pm_id = cls.ogone.ogone_s2s_form_process({
            'cc_number': '42'*8,
            'cc_cvc': '123',
            'cc_holder_name': 'test guy',
            'cc_expiry': '01/25',
            'cc_brand': 'visa',
            'acquirer_id': cls.ogone.id,
            'partner_id': cls.buyer_id
        }).id

    @mute_logger('odoo.addons.payment_ingenico.models.payment')
    def test_ogone_s2s_do_transaction(self):
        self.assertEqual(self.ogone.state, 'test', 'test without test environment')

        tx = self.env['payment.transaction'].create({
            'amount': 0.01,
            'acquirer_id': self.ogone.id,
            'currency_id': self.currency_euro.id,
            'reference': 'test_tx_ref_%s' % time.time(),
            'partner_id': self.buyer_id,
            'payment_token_id': self.pm_id,
            'type': 'server2server',
        })

        res = tx.s2s_do_transaction()

        self.assertTrue(res)

    @mute_logger('odoo.addons.payment_ingenico.models.payment')
    def test_ogone_s2s_do_transaction_manual(self):
        self.assertEqual(self.ogone.state, 'test', 'test without test environment')

        tx = self.env['payment.transaction'].create({
            'amount': 0.01,
            'acquirer_id': self.ogone.id,
            'currency_id': self.currency_euro.id,
            'reference': 'test_tx_ref_%s' % time.time(),
            'partner_id': self.buyer_id,
            'payment_token_id': self.pm_id,
            'type': 'server2server',
        })
        self.ogone.capture_manually = True

        tx.with_context(capture_manually=True).s2s_do_transaction()
        res = tx.s2s_capture_transaction()

        self.assertTrue(res)
