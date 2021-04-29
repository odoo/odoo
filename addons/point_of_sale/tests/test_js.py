# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged("post_install", "-at_install")
class PointOfSaleModelInvariants(TestPoSCommon):
    """Test suite for the invariants of PointOfSaleModel of the POS UI.

    Invariants because these tests shouldn't fail regardless of any patching
    done on the model.

    Basically, this test suite doesn't aim to test all features of the
    PointOfSaleModel, only the features which behavior are known to be
    absolute. This means that when you patched PointOfSaleModel and it resulted
    to failure in this suite, then the patch will likely negaticely affect the
    overall behavior of the PointOfSaleModel.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cash_rounding_DOWN = cls.env['account.cash.rounding'].create({
            'name': 'add_invoice_line',
            'rounding': 0.05,
            'strategy': 'add_invoice_line',
            'profit_account_id': cls.company_data['default_account_revenue'].copy().id,
            'loss_account_id': cls.company_data['default_account_expense'].copy().id,
            'rounding_method': 'DOWN',
        })
        cls.cash_rounding_HALF_UP = cls.env['account.cash.rounding'].create({
            'name': 'add_invoice_line',
            'rounding': 0.05,
            'strategy': 'add_invoice_line',
            'profit_account_id': cls.company_data['default_account_revenue'].copy().id,
            'loss_account_id': cls.company_data['default_account_expense'].copy().id,
            'rounding_method': 'HALF-UP',
        })

    def test_independent_to_config(self):
        self.basic_config.open_session_cb(check_coa=False)
        url = "/pos/ui/tests?&filenames=test_NumberBuffer,test_posRound&mod=web&failfast"
        self.browser_js(url, "", "", login="accountman", timeout=1800)

    def test_Rounding_UP(self):
        self.basic_config.open_session_cb(check_coa=False)
        self.basic_config.cash_rounding = True
        self.basic_config.only_round_cash_method = True
        self.basic_config.rounding_method = self.cash_rounding_a
        self.browser_js("/pos/ui/tests?&filenames=test_Rounding_UP&mod=web&failfast", "", "", login="accountman", timeout=1800)

    def test_Rounding_DOWN(self):
        self.basic_config.open_session_cb(check_coa=False)
        self.basic_config.cash_rounding = True
        self.basic_config.only_round_cash_method = True
        self.basic_config.rounding_method = self.cash_rounding_DOWN
        self.browser_js("/pos/ui/tests?&filenames=test_Rounding_DOWN&mod=web&failfast", "", "", login="accountman", timeout=1800)

    def test_Rounding_HALF_UP(self):
        self.basic_config.open_session_cb(check_coa=False)
        self.basic_config.cash_rounding = True
        self.basic_config.only_round_cash_method = True
        self.basic_config.rounding_method = self.cash_rounding_HALF_UP
        self.browser_js("/pos/ui/tests?&filenames=test_Rounding_HALF_UP&mod=web&failfast", "", "", login="accountman", timeout=1800)
