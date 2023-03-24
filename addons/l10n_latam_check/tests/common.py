# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nLatamCheckTest(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        chart_template = cls.company_data['company'].chart_template_id

        cls.company_data_3 = cls.setup_company_data(
            'company_3_data', chart_template=chart_template, **{'country_id': cls.env.ref('base.ar').id})

        cls.bank_journal = cls.company_data_3['default_journal_bank']
        # enable use electronic/deferred checks on bank journal
        cls.bank_journal.l10n_latam_manual_checks = True
        third_party_checks_journals = cls.env['account.journal'].search([('outbound_payment_method_line_ids.code', '=', 'new_third_party_checks'), ('inbound_payment_method_line_ids.code', '=', 'out_third_party_checks'), ('inbound_payment_method_line_ids.code', '=', 'new_third_party_checks')])
        cls.third_party_check_journal = third_party_checks_journals[0]
        cls.rejected_check_journal = third_party_checks_journals[1]

        cls.assertTrue(cls.third_party_check_journal, 'Third party check journal was not created so we can run the tests')
        cls.assertTrue(cls.rejected_check_journal, 'Rejected check journal was not created so we can run the tests')
