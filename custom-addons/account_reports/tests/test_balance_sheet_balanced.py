# pylint: disable=C0326
import logging
import itertools
import contextlib

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account import SYSCOHADA_LIST

from odoo.tests import tagged
from odoo import fields


_logger = logging.getLogger(__name__)
syscohada_coas = [country_code.lower() for country_code in SYSCOHADA_LIST]


# === Set this variable to something truthy if you want the test to identify any incorrectly-referenced accounts for you. === #
IDENTIFY_INCORRECT_ACCOUNTS = False
# === Set this to True (if the above is set to True) if you want the test to show you journal entries for reproducing the imbalance === #
EXTRA_DETAIL = False

# === When creating a new Balance Sheet, please add its config here. === #
''' Example config:
REPORT_CONFIG = {
    <Balance Sheet report xmlid> : {
        'asset_line_ref': <Total Assets line xmlid>
        'liability_line_ref': <Total Liabilities line xmlid>
        'equity_line_ref': (optional) <Total Equity line xmlid> (if not included in Liabilities)
        'balance_col_label': (optional) <expression_label of the report column containing the totals> (if different from 'balance')
        'chart_template_refs': (optional) <list of CoAs for which the report should be tested (by default any CoA on which the report is available)>
    },
} '''

REPORT_CONFIG = {
    'account_reports.balance_sheet': {
        'asset_line_ref': 'account_reports.account_financial_report_total_assets0',
        'liability_line_ref': 'account_reports.account_financial_report_liabilities_and_equity_view0',
    },
    'l10n_at_reports.account_financial_report_l10n_at_paragraph_224_ugb': {
        'asset_line_ref': 'l10n_at_reports.account_financial_report_l10n_at_paragraph_224_ugb_line_activa',
        'liability_line_ref': 'l10n_at_reports.account_financial_report_l10n_at_paragraph_224_ugb_line_passiva',
    },
    'l10n_be_reports.account_financial_report_bs_asso_a': {
        'asset_line_ref': 'l10n_be_reports.account_financial_report_bs_asso_a_a_tot',
        'liability_line_ref': 'l10n_be_reports.account_financial_report_bs_asso_a_el_tot',
    },
    'l10n_be_reports.account_financial_report_bs_asso_f': {
        'asset_line_ref': 'l10n_be_reports.account_financial_report_bs_asso_f_a_tot',
        'liability_line_ref': 'l10n_be_reports.account_financial_report_bs_asso_f_el_tot',
    },
    'l10n_be_reports.account_financial_report_bs_comp_acap': {
        'asset_line_ref': 'l10n_be_reports.account_financial_report_bs_comp_acap_a_tot',
        'liability_line_ref': 'l10n_be_reports.account_financial_report_bs_comp_acap_el_tot',
    },
    'l10n_be_reports.account_financial_report_bs_comp_acon': {
        'asset_line_ref': 'l10n_be_reports.account_financial_report_bs_comp_acon_a_tot',
        'liability_line_ref': 'l10n_be_reports.account_financial_report_bs_comp_acon_el_tot',
    },
    'l10n_be_reports.account_financial_report_bs_comp_fcap': {
        'asset_line_ref': 'l10n_be_reports.account_financial_report_bs_comp_fcap_a_tot',
        'liability_line_ref': 'l10n_be_reports.account_financial_report_bs_comp_fcap_el_tot',
    },
    'l10n_be_reports.account_financial_report_bs_comp_fcon': {
        'asset_line_ref': 'l10n_be_reports.account_financial_report_bs_comp_fcon_a_tot',
        'liability_line_ref': 'l10n_be_reports.account_financial_report_bs_comp_fcon_el_tot',
    },
    'l10n_bg_reports.l10n_bg_bs': {
        'asset_line_ref': 'l10n_bg_reports.l10n_bg_bs_assets',
        'liability_line_ref': 'l10n_bg_reports.l10n_bg_bs_liabilities',
    },
    'l10n_bo_reports.l10n_bo_bs': {
        'asset_line_ref': 'l10n_bo_reports.l10n_bo_bs_assets',
        'liability_line_ref': 'l10n_bo_reports.l10n_bo_bs_liabilities_plus_equity',
    },
    'l10n_br_reports.account_financial_report_br_balancesheet0': {
        'asset_line_ref': 'l10n_br_reports.account_financial_report_total_assets0',
        'liability_line_ref': 'l10n_br_reports.account_financial_report_liabilities_view0',
    },
    'l10n_ca_reports.l10n_ca_balance_sheet': {
        'asset_line_ref': 'l10n_ca_reports.l10n_ca_bs_assets',
        'liability_line_ref': 'l10n_ca_reports.l10n_ca_bs_equity_liability',
    },
    'l10n_ch_reports.account_financial_report_l10n_ch_bilan': {
        'asset_line_ref': 'l10n_ch_reports.account_financial_report_line_ch_1',
        'liability_line_ref': 'l10n_ch_reports.account_financial_report_line_ch_2',
    },
    'l10n_cl_reports.cl_eightcolumns_report': {
        'chart_template_refs': [],
    },
    'l10n_co_reports.l10n_co_bs_report': {
        'asset_line_ref': 'l10n_co_reports.l10n_co_bs_report_assets',
        'liability_line_ref': 'l10n_co_reports.l10n_co_bs_report_liabilities_equity',
    },
    'l10n_cy_reports.l10n_cy_balance_sheet': {
        'asset_line_ref': 'l10n_cy_reports.account_financial_report_cy_active_line',
        'liability_line_ref': 'l10n_cy_reports.account_financial_report_cy_passive_line',
    },
    'l10n_cz_reports.balance_sheet_l10n_cz_reports': {
        'asset_line_ref': 'l10n_cz_reports.l10n_cz_reports_bs_aktiva',
        'liability_line_ref': 'l10n_cz_reports.l10n_cz_reports_bs_pasiva',
        'balance_col_label': 'net',
    },
    'l10n_de_reports.balance_sheet_l10n_de': {
        'asset_line_ref': 'l10n_de_reports.skr_asset_total',
        'liability_line_ref': 'l10n_de_reports.skr_liabilities_total',
    },
    'l10n_dk_reports.account_balance_report_l10n_dk_balance': {
        'asset_line_ref': 'l10n_dk_reports.account_balance_report_l10n_dk_active',
        'liability_line_ref': 'l10n_dk_reports.account_balance_report_l10n_dk_passiv',
    },
    'l10n_do_reports.l10n_do_bs': {
        'asset_line_ref': 'l10n_do_reports.l10n_do_bs_assets',
        'liability_line_ref': 'l10n_do_reports.l10n_do_bs_liabilities_plus_equity',
    },
    'l10n_dz_reports.l10n_dz_bs': {
        'asset_line_ref': 'l10n_dz_reports.l10n_dz_bs_assets',
        'liability_line_ref': 'l10n_dz_reports.l10n_dz_bs_liabilities',
        'balance_col_label': 'net',
    },
    'l10n_ec_reports.l10n_ec_balance_sheet': {
        'asset_line_ref': 'l10n_ec_reports.l10n_ec_balance_sheet_assets',
        'liability_line_ref': 'l10n_ec_reports.l10n_ec_balance_sheet_liabilities_and_equity',
    },
    'l10n_ee_reports.account_financial_report_bs': {
        'asset_line_ref': 'l10n_ee_reports.account_financial_report_bs_assets',
        'liability_line_ref': 'l10n_ee_reports.account_financial_report_bs_liabilities_equity',
    },
    'l10n_es_reports.financial_report_balance_sheet_assoc': {
        'asset_line_ref': 'l10n_es_reports.balance_assoc_line_10000',
        'liability_line_ref': 'l10n_es_reports.balance_assoc_line_30000',
    },
    'l10n_es_reports.financial_report_balance_sheet_full': {
        'asset_line_ref': 'l10n_es_reports.balance_full_line_10000',
        'liability_line_ref': 'l10n_es_reports.balance_full_line_30000',
    },
    'l10n_es_reports.financial_report_balance_sheet_pymes': {
        'asset_line_ref': 'l10n_es_reports.balance_pymes_line_10000',
        'liability_line_ref': 'l10n_es_reports.balance_pymes_line_30000',
    },
    'l10n_fi_reports.account_financial_report_l10n_fi_bs': {
        'asset_line_ref': 'l10n_fi_reports.account_financial_report_l10n_fi_bs_line_1',
        'liability_line_ref': 'l10n_fi_reports.account_financial_report_l10n_fi_bs_line_2',
    },
    'l10n_fr_reports.account_financial_report_l10n_fr_bilan': {
        'asset_line_ref': 'l10n_fr_reports.account_financial_report_fr_bilan_actif_total',
        'liability_line_ref': 'l10n_fr_reports.account_financial_report_fr_bilan_passif_total',
        'balance_col_label': 'net',
    },
    'l10n_gr_reports.l10n_gr_bs_accounting_report': {
        'asset_line_ref': 'l10n_gr_reports.l10n_gr_bs_assets',
        'liability_line_ref': 'l10n_gr_reports.l10n_gr_bs_equity_provisions_liabilities',
    },
    'l10n_hr_reports.l10n_hr_balance_sheet': {
        'asset_line_ref': 'l10n_hr_reports.account_financial_report_hr_active_title0',
        'liability_line_ref': 'l10n_hr_reports.account_financial_report_hr_passif_title0',
        'chart_template_refs': ['hr'],  # don't test the hr_kuna CoA anymore (obsolete)
    },
    'l10n_hu_reports.l10n_hu_balance_sheet': {
        'asset_line_ref': 'l10n_hu_reports.l10n_hu_balance_sheet_assets',
        'liability_line_ref': 'l10n_hu_reports.l10n_hu_balance_sheet_liabilities',
    },
    'l10n_ie_reports.l10n_ie_bs': {
        'asset_line_ref': 'l10n_ie_reports.l10n_ie_bs_assets_total',
        'liability_line_ref': 'l10n_ie_reports.l10n_ie_bs_liabilities_total',
    },
    'l10n_it_reports.account_financial_report_it_sp': {
        'asset_line_ref': 'l10n_it_reports.account_financial_report_line_it_sp_assets_total',
        'liability_line_ref': 'l10n_it_reports.account_financial_report_line_it_sp_passif_total',
    },
    'l10n_it_reports.account_financial_report_it_sp_reduce': {
        'asset_line_ref': 'l10n_it_reports.account_financial_report_line_it_sp_reduce_assets_total',
        'liability_line_ref': 'l10n_it_reports.account_financial_report_line_it_sp_reduce_passif_total',
    },
    'l10n_ke_reports.account_financial_report_ke_bs': {
        'asset_line_ref': 'l10n_ke_reports.account_financial_report_ke_bs_A',
        'liability_line_ref': 'l10n_ke_reports.account_financial_report_ke_bs_B',
    },
    'l10n_kz_reports.l10n_kz_bl_report': {
        'asset_line_ref': 'l10n_kz_reports.l10n_kz_bl_assets',
        'liability_line_ref': 'l10n_kz_reports.l10n_kz_bl_equity_liabilities',
    },
    'l10n_lt_reports.account_financial_report_balancesheet_lt': {
        'asset_line_ref': 'l10n_lt_reports.account_financial_html_report_line_bs_lt_debit',
        'liability_line_ref': 'l10n_lt_reports.account_financial_html_report_line_bs_lt_credit',
    },
    'l10n_lu_reports.account_financial_report_l10n_lu_bs_abr': {
        'asset_line_ref': 'l10n_lu_reports.account_financial_report_l10n_lu_bs_abr_line_1_6',
        'liability_line_ref': 'l10n_lu_reports.account_financial_report_l10n_lu_bs_abr_line_2_5',
    },
    'l10n_lu_reports.account_financial_report_l10n_lu_bs': {
        'asset_line_ref': 'l10n_lu_reports.account_financial_report_l10n_lu_bs_line_1_6',
        'liability_line_ref': 'l10n_lu_reports.account_financial_report_l10n_lu_bs_line_2_5',
    },
    'l10n_lv_reports.l10n_lv_balance_sheet': {
        'asset_line_ref': 'l10n_lv_reports.account_financial_report_lv_active_title',
        'liability_line_ref': 'l10n_lv_reports.account_financial_report_lv_passif_title',
    },
    'l10n_ma_reports.account_financial_report_bs': {
        'asset_line_ref': 'l10n_ma_reports.account_financial_report_bs_a_total',
        'liability_line_ref': 'l10n_ma_reports.account_financial_report_bs_p_total',
        'balance_col_label': 'net',
    },
    'l10n_mn_reports.account_report_balancesheet': {
        'asset_line_ref': 'l10n_mn_reports.report_line_balanceta',
        'liability_line_ref': 'l10n_mn_reports.report_line_balancele',
    },
    'l10n_mt_reports.l10n_mt_balance_sheet': {
        'asset_line_ref': 'l10n_mt_reports.account_financial_report_mt_active_title',
        'liability_line_ref': 'l10n_mt_reports.account_financial_report_mt_passif_title',
    },
    'l10n_mz_reports.l10_mz_bs': {
        'asset_line_ref': 'l10n_mz_reports.l10n_mz_bs_line_1',
        'liability_line_ref': 'l10n_mz_reports.l10n_mz_bs_line_2',
    },
    'l10n_nl_reports.account_financial_report_bs': {
        'asset_line_ref': 'l10n_nl_reports.account_financial_report_bs_assets',
        'liability_line_ref': 'l10n_nl_reports.account_financial_report_bs_leq',
    },
    'l10n_no_reports.account_financial_report_NO_balancesheet': {
        'asset_line_ref': 'l10n_no_reports.account_financial_report_NO_active',
        'liability_line_ref': 'l10n_no_reports.account_financial_report_NO_passive',
    },
    'l10n_pe_reports.account_financial_report_bs': {
        'asset_line_ref': 'l10n_pe_reports.account_financial_report_bs_A_TOTAL',
        'liability_line_ref': 'l10n_pe_reports.account_financial_report_bs_EL',
    },
    'l10n_pk_reports.account_financial_report_pk_balancesheet0': {
        'asset_line_ref': 'l10n_pk_reports.account_balance_report_pk_asset',
        'liability_line_ref': 'l10n_pk_reports.account_balance_report_pk_equity_plus_liabilities',
    },
    'l10n_pl_reports.l10n_pl_micro_bs': {
        'asset_line_ref': 'l10n_pl_reports.l10n_pl_micro_bs_assets',
        'liability_line_ref': 'l10n_pl_reports.l10n_pl_micro_bs_passives',
    },
    'l10n_pl_reports.l10n_pl_small_bs': {
        'asset_line_ref': 'l10n_pl_reports.l10n_pl_small_bs_assets',
        'liability_line_ref': 'l10n_pl_reports.l10n_pl_small_bs_passives',
    },
    'l10n_pt_reports.account_financial_report_line_pt_balanco': {
        'asset_line_ref': 'l10n_pt_reports.account_financial_report_line_pt_balanco_total_do_ativo',
        'liability_line_ref': 'l10n_pt_reports.account_financial_report_line_pt_balanco_total_do_capital_proprio_e_do_passivo',
    },
    'l10n_ro_reports.account_financial_report_ro_bs_smle': {
        'asset_line_ref': 'l10n_ro_reports.account_financial_report_ro_bs_smle_total_assets',
        'liability_line_ref': 'l10n_ro_reports.account_financial_report_ro_bs_smle_total_liabilities',
    },
    'l10n_ro_reports.account_financial_report_ro_bs_large': {
        'asset_line_ref': 'l10n_ro_reports.account_financial_report_ro_bs_large_total_assets',
        'liability_line_ref': 'l10n_ro_reports.account_financial_report_ro_bs_large_total_liabilities',
    },
    'l10n_rs_reports.account_financial_report_rs_BS': {
        'asset_line_ref': 'l10n_rs_reports.account_financial_report_rs_BS_assets',
        'liability_line_ref': 'l10n_rs_reports.account_financial_report_rs_BS_equity_liabilities',
    },
    'l10n_rw_reports.l10n_rw_balance_sheet': {
        'asset_line_ref': 'l10n_rw_reports.account_financial_report_rw_active',
        'liability_line_ref': 'l10n_rw_reports.account_financial_report_rw_passive',
    },
    'l10n_se_reports.account_financial_report_bs': {
        'asset_line_ref': 'l10n_se_reports.account_financial_report_bs_A_TOTAL',
        'liability_line_ref': 'l10n_se_reports.account_financial_report_bs_EL_TOTAL',
    },
    'l10n_si_reports.l10n_si_balance_sheet': {
        'asset_line_ref': 'l10n_si_reports.l10n_si_balance_sheet_resources',
        'liability_line_ref': 'l10n_si_reports.l10n_si_balance_sheet_liabilities',
    },
    'l10n_syscohada_reports.account_financial_report_syscohada_bilan': {
        'asset_line_ref': 'l10n_syscohada_reports.account_financial_report_line_03_3_11_syscohada_bilan_actif',
        'liability_line_ref': 'l10n_syscohada_reports.account_financial_report_line_03_3_11_syscohada_bilan_passif',
        'chart_template_refs': syscohada_coas,
    },
    'l10n_tn_reports.l10n_tn_bs_account_report': {
        'asset_line_ref': 'l10n_tn_reports.l10n_tn_bs_assets',
        'liability_line_ref': 'l10n_tn_reports.l10n_tn_bs_liabilities_equity',
    },
    'l10n_tr_reports.account_report_l10n_tr_balance_sheet': {
        'asset_line_ref': 'l10n_tr_reports.account_report_line_trbs_active',
        'liability_line_ref': 'l10n_tr_reports.account_report_line_trbs_pasive',
    },
    'l10n_tw_reports.balance_sheet_l10n_tw': {
        'asset_line_ref': 'l10n_tw_reports.account_financial_report_total_assets0_l10n_tw',
        'liability_line_ref': 'l10n_tw_reports.account_financial_report_libailities_and_equity',
    },
    'l10n_tz_reports.l10n_tz_balance_sheet': {
        'asset_line_ref': 'l10n_tz_reports.account_financial_report_tz_active',
        'liability_line_ref': 'l10n_tz_reports.account_financial_report_tz_passive',
    },
    'l10n_zm_reports.balance_sheet_zm': {
        'asset_line_ref': 'l10n_zm_reports.balance_sheet_zm_assets',
        'liability_line_ref': 'l10n_zm_reports.balance_sheet_zm_liabilities_and_equities',
    },
}

# === If some accounts should be excluded from the testing, specify them here === #
# Accounts starting with 99 are excluded anyway: users should change their codes
# to something sensible in order for them to be taken into account in the Balance Sheet.
'''
NON_TESTED_ACCOUNTS = {
    <chart template ref>: [account_code_1, account_code_2, ...]
}
'''
NON_TESTED_ACCOUNTS = {
    'all': [
        '99',  # 99 account codes are placeholders and should normally be changed by the user.
        '123456'  # hr.payroll creates an account 123456 Account Payslip Houserental for demo companies; don't test it
    ],
    **{coa: ['13'] for coa in syscohada_coas},
    'at': ['98'],
    'mn': ['9301'],
    'it': ['412', '413', '9102'],
    'pt': ['811'],
}


def log_incorrect_accounts_quiet(report_setup_data, amls, totals, is_first_call):
    if is_first_call:
        _logger.error("""
                The Balance Sheet %s is not balanced.
                These accounts are incorrectly used in the Balance Sheet
                or in the Profit & Loss, if inserted into the Balance Sheet via cross-report).
                To show the journal entries that cause the imbalance,
                set the EXTRA_DETAIL global to True at the top of the test file.
            """,
            report_setup_data['report_ref'],
        )

    _logger.error('- %s %s', amls[0].account_id.code, amls[0].account_id.name)


def log_incorrect_accounts_detailed(report_setup_data, amls, totals, is_first_call):
    if is_first_call:
        _logger.error("""
                The Balance Sheet %s is not balanced.
                If you construct any of the following journal entries, Assets != Liabilities + Equity.
            """,
            report_setup_data['report_ref'],
        )

    format_params = []
    currency = amls.currency_id
    for aml in amls:
        format_params += [
            aml.date,
            f'{aml.account_id.code} {aml.account_id.name}'[:50],
            currency.format(aml.debit),
            currency.format(aml.credit),
        ]
    format_params += [
        report_setup_data['report_date'],
        currency.format(totals['total_asset']),
        currency.format(totals['total_liability']),
    ]
    error_msg = '''
        +------------+----------------------------------------------------+------------------+------------------+
        |    Date    |                        Account                     |       Debit      |      Credit      |
        +------------+----------------------------------------------------+------------------+------------------+
        | {:10} | {:<50} | {:<16} | {:<16} |
        | {:10} | {:<50} | {:<16} | {:<16} |
        +------------+----------------------------------------------------+------------------+------------------+
        Balance Sheet on {}: Total Assets: {} ; Total Liabilities + Equity: {}
    '''.format(*format_params)
    _logger.error(error_msg)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestBalanceSheetBalanced(TestAccountReportsCommon):
    ''' Diagnose unbalanced Balance Sheets.

    We do this by creating a journal entry with two journal items in each account:
    one debit and one credit. We then generate the Balance Sheet report, and check
    whether the Assets line is equal to the sum of the Liabilities and Equity lines.

    Some accounts are not checked:
    - those starting with '99' (automatically created in order to enable some
      functionalities to work, but the user is expected to change their code)
    - those included in the NON_TESTED_ACCOUNTS dict.

    The test can optionally identify guilty accounts using binary search; this can
    be toggled on by setting IDENTIFY_INCORRECT_ACCOUNTS = True.
    '''
    @classmethod
    def setUpClass(cls):
        # OVERRIDE: don't create demo companies, and don't set env.user
        super(AccountTestInvoicingCommon, cls).setUpClass()

    def test_balance_sheet_balanced(self):
        ''' The main test function: check whether every installed balance sheet is balanced. '''
        installed_modules = self.env['ir.module.module'].search([('state', '=', 'installed')])
        installed_coas = [
            name
            for mapping in installed_modules.mapped('account_templates')
            for name, template in mapping.items()
            if template['visible'] and name != 'syscohada'  # Syscohada template is visible but deprecated since odoo#163350
        ]

        self.existing_companies = self.env['res.company'].search([])

        for coa in installed_coas:
            with contextlib.closing(self.env.cr.savepoint()), self.subTest(CoA=coa):
                # === 1. Set-up localization === #
                available_reports, aml_pairs, accounts_by_aml = self._set_up_localization(coa)

                # Test each of the Balance Sheet reports available for the CoA.
                for report in available_reports:
                    report_ref = report.get_external_id()[report.id]
                    with self.subTest(Report=report_ref):
                        _logger.info('Testing report %s with CoA %s', report_ref, coa)

                        # === 2. Set-up report === #
                        report_setup_data = self._set_up_report(report)

                        # === 3. Test that the report is balanced with both the debits journal entry and the credits journal entry. === #
                        if not IDENTIFY_INCORRECT_ACCOUNTS:
                            self._check_balance_sheet_balanced(report_setup_data, aml_pairs)
                        else:
                            bad_account_ids = set()
                            logging_fn = log_incorrect_accounts_detailed if EXTRA_DETAIL else log_incorrect_accounts_quiet

                            self._identify_incorrect_accounts(
                                report_setup_data,
                                aml_pairs,
                                accounts_by_aml,
                                bad_account_ids,
                                logging_fn,
                            )
                            if bad_account_ids:
                                self.fail('Balance Sheet not balanced.')

    def _set_up_localization(self, coa):
        ''' Set up a localization for testing.

            This identifies the company to use (creating it if needed),
            sets self.env.company to it, and generates AMLs for testing.

            If a (demo) company already exists with the CoA, we'll just use it
            rather than create a new company and load a new CoA for it.

            :param account.chart.template coa: the Chart of Accounts to install

            :return: (available_reports, aml_pairs, accounts_by_aml), where:
                * available_reports are the reports that can be tested for this localization
                * aml_pairs is a list of (aml_id, counterpart_aml_id) that were generated
                * accounts_by_aml is a map {aml_id: account_id} for the generated AMLs
        '''
        # Always reset company, as the one used in the previous subtest might not exist anymore
        self.env.company = self.env['res.company'].search([], limit=1)

        coa_setup_data = {}
        if coa in self.existing_companies.mapped('chart_template'):
            self.env.company = next(iter(self.existing_companies.filtered(lambda c: c.chart_template == coa)))

            coa_setup_data['counterpart_account'] = self.env['account.account'].search([
                ('company_id', '=', self.env.company.id),
                ('account_type', '=', 'asset_receivable'),
            ], limit=1)
            coa_setup_data['income_account'] = self.env['account.account'].search([
                ('company_id', '=', self.env.company.id),
                ('internal_group', '=', 'income'),
            ], limit=1)
            coa_setup_data['journal'] = self.env['account.journal'].search([
                ('company_id', '=', self.env.company.id),
                ('type', '=', 'general')
            ], limit=1)
        else:
            company_data = self.setup_company_data('company_3', chart_template=coa)
            self.env.company = company_data['company']

            coa_setup_data['counterpart_account'] = company_data['default_account_receivable']
            coa_setup_data['income_account'] = company_data['default_account_revenue']
            coa_setup_data['journal'] = company_data['default_journal_misc']

        # Find the available Balance Sheets for the current company.
        generic_balance_sheet = self.env.ref('account_reports.balance_sheet').with_company(self.env.company)
        generic_balance_sheet.with_context(active_test=False).variant_report_ids.write({'active': True})
        available_report_ids = [variant['id'] for variant in generic_balance_sheet.get_options()['available_variants']]
        available_reports = self.env['account.report'].browse(available_report_ids)

        # Don't test Balance Sheets for which the REPORT_CONFIG specifies a chart_template_refs that differs from this CoA.
        available_report_refs = available_reports.get_external_id()
        report_ids_to_skip = [id_ for id_, report_ref in available_report_refs.items()
                              if coa not in REPORT_CONFIG.get(report_ref, {}).get('chart_template_refs', [coa])]
        available_reports -= self.env['account.report'].browse(report_ids_to_skip)
        available_reports = available_reports.with_company(self.env.company)

        # Choose an account to be a counterpart account. Every AML we generate will have a counterpart in this account.
        # We use the Accounts Receivable account (which in general should be well-configured.)
        # However, if the Balance Sheet is incorrect for the counterpart account, the test will give weird results.
        tested_accounts_domain = [
            ('company_id', '=', self.env.company.id),
            ('internal_group', '!=', 'off_balance'),
        ]
        for code in NON_TESTED_ACCOUNTS['all'] + NON_TESTED_ACCOUNTS.get(coa, []):
            tested_accounts_domain += ['!', ('code', '=like', f'{code}%')]
        tested_accounts = self.env['account.account'].search(tested_accounts_domain)
        coa_setup_data['tested_accounts'] = tested_accounts - coa_setup_data['counterpart_account']

        # Create two test journal entries: one with debits in each account (other than the counterpart account), the other with credits.
        debit_move_aml_pairs, debit_accounts_by_aml = self._create_balance_sheet_test_move(coa_setup_data)
        credit_move_aml_pairs, credit_accounts_by_aml = self._create_balance_sheet_test_move(coa_setup_data, create_credits=True)

        aml_pairs = debit_move_aml_pairs + credit_move_aml_pairs
        accounts_by_aml = {**debit_accounts_by_aml, **credit_accounts_by_aml}

        return available_reports, aml_pairs, accounts_by_aml

    def _set_up_report(self, report):
        ''' Set-up a Balance Sheet report for testing.

            :param account.report report: the Balance Sheet report to set-up

            The method sets the following keys of coa_setup_data:
                report_ref: the XMLID of the report currently being tested
                report: the report currently being tested
                report_options: the report options for the test
                report_column_balance_idx: the index of the column containing the balance
                asset_line: the Total Assets report line
                liability_line: the Total Liabilities report line
                equity_line: the Total Equity report line (if separate from Liabilities)
        '''
        report_setup_data = {'report': report}

        report_ref = report.get_external_id()[report.id]
        if report_ref not in REPORT_CONFIG:
            self.fail(f'''
                The following Balance Sheet report is installed but is not configured to be tested:
                {report_ref}
                Please add it to the REPORT_CONFIG global at the beginning of this file.''')
        report_config = REPORT_CONFIG[report_ref]

        report_setup_data['report_ref'] = report_ref

        report_setup_data['report_date'] = '2022-12-31'
        report_setup_data['report_options'] = self._generate_options(report, False, fields.Date.to_date(report_setup_data['report_date']))

        # Find the report column containing the total figures.
        for idx, col in enumerate(report_setup_data['report_options']['columns']):
            if col['expression_label'] in report_config.get('balance_col_label', 'balance'):
                report_setup_data['report_column_balance_idx'] = idx
                break
        else:
            self.fail(f'Could not identify totals column for report {report_ref} '
                      '- please add its expression_label in the REPORT_CONFIG global at the top of this file.')

        report_setup_data['asset_line'] = self.env.ref(report_config['asset_line_ref'])
        report_setup_data['liability_line'] = self.env.ref(report_config['liability_line_ref'])
        report_setup_data['equity_line'] = self.env.ref(report_config['equity_line_ref']) if 'equity_line_ref' in report_config else None

        return report_setup_data

    def _create_balance_sheet_test_move(self, coa_setup_data, create_credits=False):
        ''' Create a journal entry that will be the basis for testing the Balance Sheet.
            The created journal entry will have one AML in each account in coa_setup_data['tested_accounts'],
            and corresponding counterpart AMLs in coa_setup_data['counterpart_account'].
            We create it in SQL to improve performance (since this gets run a lot on runbot).

            :param bool create_credits: If true, the AMLs will be created with credits (instead of debits)
                                        and the counterpart AMLs will be created with debits.

            :return: (aml_pairs, accounts_by_aml), where:
               - aml_pairs is a list of tuples (aml_id, counterpart_aml_id) containing the AMLs of the journal entry that was created.
               - accounts_by_aml is a map of AML id to account id.
        '''

        def get_move_line_sql_create_vals(move, account, balance):
            debit, credit = (balance, 0.0) if balance > 0.0 else (0.0, -balance)
            return {
                'account_id': account.id,
                'balance': balance,
                'debit': debit,
                'credit': credit,
                'company_id': move.company_id.id,
                'currency_id': move.company_id.currency_id.id,
                'date': move.date,
                'display_type': 'product',
                'journal_id': move.journal_id.id,
                'move_id': move.id,
            }

        move = self.env['account.move'].create({
            'name': False,
            'date': '2022-06-01',
            'move_type': 'entry',
            'journal_id': coa_setup_data['journal'].id,
        })

        # For each account, we create 2 AMLs:
        # - one AML in that account (either a debit or a credit, depending on the create_credits param)
        # - one counterpart AML in the counterpart account
        amls_vals = []
        for i, account in enumerate(coa_setup_data['tested_accounts']):
            balance = self.env.company.currency_id.round(i + 1)
            if not create_credits:
                balance = -balance
            amls_vals += [
                get_move_line_sql_create_vals(move, account, balance),
                get_move_line_sql_create_vals(move, coa_setup_data['counterpart_account'], -balance),
            ]

        move_previous_year = self.env['account.move'].create({
            'name': False,
            'date': '2021-12-31',
            'move_type': 'entry',
            'journal_id': coa_setup_data['journal'].id,
        })

        # Additionally, in one Income/Expense account, create an AML in the previous fiscal year
        # in order to test the unaffected earnings
        amls_vals += [
            get_move_line_sql_create_vals(move_previous_year, coa_setup_data['income_account'], balance),
            get_move_line_sql_create_vals(move_previous_year, coa_setup_data['counterpart_account'], -balance),
        ]

        # Create the AMLs
        query_columns = ', '.join(amls_vals[0].keys())
        query_placeholder = ', '.join("%s" for d in amls_vals)
        query_params = [tuple(d.values()) for d in amls_vals]

        self.env['account.move.line'].invalidate_model()
        self.env.cr.execute(
            f'INSERT INTO "account_move_line" ({query_columns}) VALUES {query_placeholder} RETURNING "id"',
            query_params,
        )
        aml_ids = [aml_id for aml_id, in self.env.cr.fetchall()]

        # Create a map of AMLs to accounts, to avoid having to fetch this info from the DB
        accounts_by_aml = {aml_ids[i]: aml_vals['account_id'] for i, aml_vals in enumerate(amls_vals)}

        # Group AMLs in account/counterpart pairs
        aml_pairs = []
        for i, account in enumerate(coa_setup_data['tested_accounts']):
            aml_id = aml_ids[2 * i]
            counterpart_aml_id = aml_ids[2 * i + 1]
            aml_pairs.append((aml_id, counterpart_aml_id))

        return aml_pairs, accounts_by_aml

    def _check_balance_sheet_balanced(self, report_setup_data, aml_pairs):
        ''' Check whether the Balance Sheet is balanced. '''
        # Set 'parent_state' to 'posted' on the AMLs of the debits journal entry, and to 'draft' on all other AMLs.
        with self._activate_lines(aml_pairs):
            totals = self._get_report_totals(report_setup_data)
            if not totals['is_balanced']:
                self.fail(f'''
                    The balance sheet {report_setup_data['report_ref']} is not balanced.
                    Total Assets: {totals['total_asset']}; Total Liabilities + Equity: {totals['total_liability']}.
                    This test can also find out for you which accounts are incorrectly used in the Balance Sheet.
                    To do this, set the IDENTIFY_INCORRECT_ACCOUNTS variable at the top of this file to something truthy.
                ''')

    @contextlib.contextmanager
    def _activate_lines(self, aml_pairs):
        ''' On entry: set the 'parent_state' of the specified AMLs to 'posted'.
            On exit: set the 'parent_state' of these AMLs to 'draft'.

            :param aml_pairs: list of tuples (aml_id, counterpart_aml_id) whose parent_state should be set to 'posted'.
        '''
        aml_ids = tuple(itertools.chain(*aml_pairs))
        self.env['account.move.line'].browse(aml_ids).invalidate_recordset()
        self.env.cr.execute(
            '''
            UPDATE account_move_line
               SET parent_state = 'posted'
             WHERE id IN %s
            ''',
            [aml_ids]
        )
        yield

        self.env.cr.execute(
            '''
            UPDATE account_move_line
               SET parent_state = 'draft'
             WHERE id IN %s
            ''',
            [aml_ids]
        )

    def _get_report_totals(self, report_setup_data):
        ''' Get the Assets, Liabilities and Equity totals of the Balance Sheet report. '''

        def get_line_amount(lines, report_line, balance_column_idx):
            line = next(filter(lambda line: self.env['account.report']._get_res_id_from_line_id(line['id'], 'account.report.line') == report_line.id, lines))
            balance = line['columns'][balance_column_idx]['no_format']
            self.assertIsNotNone(balance, f'Report line "{report_line.name}" does not set a value in the column which should contain the balance.')
            return balance

        lines = report_setup_data['report']._get_lines(report_setup_data['report_options'])

        balance_column_idx = report_setup_data['report_column_balance_idx']

        total_asset = get_line_amount(lines, report_setup_data['asset_line'], balance_column_idx)
        total_liability = (
            get_line_amount(lines, report_setup_data['liability_line'], balance_column_idx)
            + (get_line_amount(lines, report_setup_data['equity_line'], balance_column_idx) if report_setup_data['equity_line'] else 0.0)
        )

        return {
            'total_asset': total_asset,
            'total_liability': total_liability,
            'is_balanced': self.env.company.currency_id.compare_amounts(total_asset, total_liability) == 0
        }

    def _identify_incorrect_accounts(self, report_setup_data, aml_pairs, accounts_by_aml, bad_account_ids, logging_fn):
        ''' Identify accounts that are incorrectly used in the Balance Sheet, using a binary search.
            This is a recursive function.

            :param report_setup_data: The report configuration to test
            :param aml_pairs: a list of tuples (aml_id, counterpart_aml_id)
                              account.move.lines which cause the Balance Sheet to be unbalanced.
            :param accounts_by_aml: a map {aml_id: account_id} of the AMLs to test
            :param bad_account_ids: a set of account ids that are determined to be badly referenced,
                                    can be used to avoid testing a bad account twice
            :param logging_fn: a function to call when an account causing an unbalance is found. This should take
                               as first argument a pair (aml_id, counterpart_aml_id) and
                               as second argument a dict containing information about the report totals
        '''

        # No need to further test AMLs in accounts already determined to be badly referenced.
        aml_pairs = [
            (aml_id, counterpart_aml_id)
            for aml_id, counterpart_aml_id in aml_pairs
            if accounts_by_aml[aml_id] not in bad_account_ids
        ]
        if not aml_pairs:
            return
        with self._activate_lines(aml_pairs):
            totals = self._get_report_totals()

        if totals['is_balanced']:
            # Valid subtree case. There are no badly-referenced accounts in the subtree, just return (no need to search deeper)
            return
        elif len(aml_pairs) == 1:
            # Leaf case. This account is badly-referenced: log and return.
            logging_fn(
                report_setup_data,
                amls=self.env['account.move.line'].browse(aml_pairs[0]),
                totals=totals,
                is_first_call=not bad_account_ids,
            )
            bad_account_ids.add(accounts_by_aml[aml_pairs[0][0]])
        else:
            # Non-leaf case. Some accounts in the subtree are badly-referenced: bisect it into two halves, and check each half.
            middle_index = len(aml_pairs) // 2
            aml_pairs_left = aml_pairs[:middle_index]
            aml_pairs_right = aml_pairs[middle_index:]
            self._identify_incorrect_accounts(report_setup_data, aml_pairs_left, accounts_by_aml, bad_account_ids, logging_fn)
            self._identify_incorrect_accounts(report_setup_data, aml_pairs_right, accounts_by_aml, bad_account_ids, logging_fn)
