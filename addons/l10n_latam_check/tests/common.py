# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nLatamCheckTest(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.chart_template = cls.company_data['company'].chart_template
        cls.ar_company_data = cls.setup_other_company(name='ar_company', country_id=cls.env.ref('base.ar').id)
        cls.ar_company = cls.env['res.company'].search([('name', '=', 'ar_company')])

        cls.bank_journal = cls.ar_company_data['default_journal_bank']
        outstanding_payment_account = cls.env['account.account'].with_company(cls.ar_company.id).create({
            'name': "Latam Test Outstanding Payments",
            'code': 'OSTP01',
            'reconcile': True,
            'account_type': 'asset_current',
        })
        cls.bank_journal.outstanding_payment_account_id = outstanding_payment_account

        cls.third_party_check_journal = cls.env['account.journal'].with_company(cls.ar_company.id).create({
            'name': 'Test Third Party Checks',
            'type': 'cash',
            'outstanding_payment_account_id': outstanding_payment_account.id,
        })
        cls.rejected_check_journal = cls.env['account.journal'].with_company(cls.ar_company.id).create({
            'name': 'Test Rejected Third Party Checks',
            'type': 'cash',
            'outstanding_payment_account_id': outstanding_payment_account.id,
        })

        cls.assertTrue(cls.third_party_check_journal, 'Third party check journal was not created so we can run the tests')
        cls.assertTrue(cls.rejected_check_journal, 'Rejected check journal was not created so we can run the tests')

        cls.own_checks_method = cls.get_payment_methods('own_checks', cls.env.company)
