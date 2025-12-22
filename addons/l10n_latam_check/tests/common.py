# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import tagged
from odoo import Command


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nLatamCheckTest(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.chart_template = cls.company_data['company'].chart_template
        cls.company_data_3 = cls.setup_other_company(name='company_3_data', country_id=cls.env.ref('base.ar').id)

        cls.bank_journal = cls.company_data_3['default_journal_bank']
        cls.bank_journal.outbound_payment_method_line_ids = [
            Command.create({'payment_method_id': cls.env.ref('l10n_latam_check.account_payment_method_own_checks').id, 'name': 'Own Checks'}),
            Command.create({'payment_method_id': cls.env.ref('l10n_latam_check.account_payment_method_out_third_party_checks').id, 'name': 'Rejected Check'}),
        ]
        # enable use electronic/deferred checks on bank journal
        third_party_checks_journals = cls.env['account.journal'].search([
            ('inbound_payment_method_line_ids.code', '=', 'in_third_party_checks'),
            ('inbound_payment_method_line_ids.code', '=', 'new_third_party_checks'),
            ('outbound_payment_method_line_ids.code', 'in', ('out_third_party_checks', 'return_third_party_checks')),
        ])
        cls.third_party_check_journal = third_party_checks_journals[0]
        cls.rejected_check_journal = third_party_checks_journals[1]

        cls.assertTrue(cls.third_party_check_journal, 'Third party check journal was not created so we can run the tests')
        cls.assertTrue(cls.rejected_check_journal, 'Rejected check journal was not created so we can run the tests')

        for company, journals in third_party_checks_journals.grouped('company_id').items():
            outstanding_account = cls.outbound_payment_method_line.payment_account_id.copy({'company_ids': [Command.set(company.ids)]})
            cls.bank_journal.outbound_payment_method_line_ids.filtered(lambda m: m.company_id == company).payment_account_id = outstanding_account
