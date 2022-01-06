# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from addons.account.tests.account_test_savepoint import AccountTestInvoicingCommon
from addons.account.tests.test_account_move_out_invoice import TestAccountMoveOutInvoiceOnchanges
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class PortugalQRCodeTest(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_pt.pt_chart_template'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['company'].write({
            'city': 'Lisboa',
            'zip': '1234-789',
            'vat': '123456789',
            'company_registry': '123456',
            'phone': '+47 11 11 11 11',
            'country_id': cls.env.ref('base.pt').id,
        })

    def test_multiple_taxes(self):
        pass

    def test_different_currency(self):
        pass

    def test_credit_note(self):
        pass
