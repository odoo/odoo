# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import tagged
from odoo import Command


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nLatamCheckTest(AccountTestInvoicingCommon):

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.bank_journal = cls.company_data['default_journal_bank']
        cls._setup_check_payment_methods(cls.bank_journal)

    @classmethod
    def _setup_check_payment_methods(cls, bank_journal):
        bank_journal.outbound_payment_method_line_ids = [
            Command.create({'payment_method_id': cls.env.ref('l10n_latam_check.account_payment_method_own_checks').id, 'name': 'Own Checks'}),
            Command.create({'payment_method_id': cls.env.ref('l10n_latam_check.account_payment_method_out_third_party_checks').id, 'name': 'Rejected Check'}),
        ]
        bank_journal._assign_outstanding_account_to_payment_method_lines(
            'outbound',
            payment_method_codes=('own_checks', 'out_third_party_checks'),
            chart_template=bank_journal.company_id.chart_template,
        )
