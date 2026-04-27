# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pdb

from odoo.tests.common import tagged, TransactionCase
from odoo.tools import file_open
from odoo import Command
from odoo.tests import HttpCase, tagged, TransactionCase

import json
from datetime import datetime, date
from freezegun import freeze_time
from collections import defaultdict
from unittest.mock import patch


_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install', 'swissdec_payroll')
class TestSwissdecCommon(TransactionCase):
    @classmethod
    def _l10n_ch_generate_swissdec_demo_payslip(cls, contract, date_from, date_to, company, after_payment=False):
        batch = cls.env['hr.payslip.run'].search(
            [('date_start', '=', date_from), ('company_id', '=', company)])
        if not batch:
            batch = cls.env['hr.payslip.run'].create({
                'name': f"Monthly Pay Batch - {date_from.year}-{date_from.month}",
                'date_start': date_from,
                'date_end': date_to,
                'company_id': company,
            })
        vals = {
            'name': f"Monthly Pay Batch - {date_from.year}-{date_from.month}",
            'employee_id': contract.employee_id.id,
            'contract_id': contract.id,
            'company_id': company,
            'struct_id': cls.env.ref('l10n_ch_hr_payroll_elm_transmission.hr_payroll_structure_ch_elm').id,
            'date_from': date_from,
            'date_to': date_to,
            'l10n_ch_after_departure_payment': after_payment,
            'payslip_run_id': batch.id,
        }
        payslip = cls.env['hr.payslip'].with_context(tracking_disable=True).create(vals)
        cls.env.flush_all()
        payslip.compute_sheet()
        payslip.action_payslip_done()

        return payslip

    @classmethod
    def _l10n_ch_compute_swissdec_demo_paylips(cls, company, date_from):
        _logger.info('Created payslips for period %s-%s', date_from.year, date_from.month)
        batch = cls._l10n_ch_create_batch(company, date_from.month, pay_13th=date_from.month == 12)
        _logger.info('Computed payslips for period %s-%s', date_from.year, date_from.month)
        return batch

    @classmethod
    def _l10n_ch_create_batch(cls, company, month, pay_13th=False):
        cls.env.flush_all()
        batch_wizard = cls.env['l10n.ch.hr.payslip.montlhy.wizard'].create({
            "company_id": company.id,
            "year": datetime.now().year,
            "month": str(month),
            "pay_13th": pay_13th
        })
        batch_action = batch_wizard.action_create()
        batch = cls.env['hr.payslip.run'].browse(batch_action['res_id'])
        batch.action_validate()
        cls.env.flush_all()
        return batch

    def _normalize_data(self, data):
        """
        Recursively transform data so that the order of lists no longer matters.
        """
        if isinstance(data, dict):
            return {k: self._normalize_data(v) for k, v in sorted(data.items(), key=lambda d: str(d))}
        elif isinstance(data, list):
            return sorted([self._normalize_data(item) for item in data], key=lambda d: str(d))
        else:
            return data

    def _get_truth_base_path(self):
        return ""

    def _compare_with_truth_base(self, declaration_type, identifier, generated_dict):
        truth_base = json.load(file_open(f'{self._get_truth_base_path()}/{declaration_type}.json')),
        truth_dict = truth_base[0].get(identifier)

        json_formated = json.loads(json.dumps(generated_dict))
        self.assertDictEqual(
            self._normalize_data(json_formated),
            self._normalize_data(truth_dict),
            f"Mismatch in declaration '{identifier}'."
        )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.maxDiff = None
        cls.env['res.company'].search([('name', '=', 'Muster AG')]).write({'name': 'Muster AG (Old)'})
        cls.muster_ag_company = cls.env['res.company'].create({
            'name': 'Muster AG',
            'street': 'Bahnhofstrasse 1',
            'zip': '6003',
            'city': 'Luzern',
            'country_id': cls.env.ref('base.ch').id,
            'l10n_ch_uid': 'CHE-999.999.996',
            'phone': '0412186532',
            'l10n_ch_30_day_method': True,
            'currency_id': cls.env.ref('base.CHF').id
        })
        cls.env.user.company_ids |= cls.muster_ag_company
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=cls.muster_ag_company.ids))

        # Load IS Rates
        rates_to_load = [
            ('LU_N_A_0', 'LU_A0N.json'),
            ('LU_N_N_0', 'LU_N0N.json'),
            ('BE_N_A_0', 'BE_A0N.json'),
            ('BE_N_A_1', 'BE_A1N.json'),
            ('BE_N_B_0', 'BE_B0N.json'),
            ('BE_N_C_0', 'BE_C0N.json'),
            ('BE_N_B_1', 'BE_B1N.json'),
            ('BE_N_H_1', 'BE_H1N.json'),
            ('BE_N_L_0', 'BE_L0N.json'),
            ('BE_HE_N', 'BE_HEN.json'),
            ('BE_ME_N', 'BE_MEN.json'),
            ('LU_NO_N', 'LU_NON.json'),
            ('BE_SF_N', 'BE_SFN.json'),
            ('TI_N_A_0', 'TI_A0N.json'),
            ('TI_N_B_0', 'TI_B0N.json'),
            ('TI_N_B_1', 'TI_B1N.json'),
            ('TI_N_C_0', 'TI_C0N.json'),
            ('TI_N_F_0', 'TI_F0N.json'),
            ('TI_N_F_1', 'TI_F1N.json'),
            ('TI_N_R_0', 'TI_R0N.json'),
            ('TI_N_T_0', 'TI_T0N.json'),
            ('VD_N_A_0', 'VD_A0N.json'),
            ('VD_N_A_1', 'VD_A1N.json'),
            ('VD_N_A_2', 'VD_A2N.json'),
            ('VD_N_B_0', 'VD_B0N.json'),
        ]
        rates_to_unlink = cls.env['hr.rule.parameter']
        for xml_id, file_name in rates_to_load:
            rates_to_unlink += cls.env['hr.rule.parameter'].search([('code', '=', f'l10n_ch_withholding_tax_rates_{xml_id}')])
        if rates_to_unlink:
            rates_to_unlink.unlink()
        for xml_id, file_name in rates_to_load:
            cls.env['hr.rule.parameter'].search([('code', '=', f'l10n_ch_withholding_tax_rates_{xml_id}')]).unlink()
            rule_parameter = cls.env['hr.rule.parameter'].create({
                'name': f'CH Withholding Tax: {xml_id}',
                'code': f'l10n_ch_withholding_tax_rates_{xml_id}',
                'country_id': cls.env.ref('base.ch').id,
            })
            cls.env['hr.rule.parameter.value'].create({
                'parameter_value': json.load(file_open(f'l10n_ch_hr_payroll_elm_transmission/tests/data/is_rates/{file_name}')),
                'rule_parameter_id': rule_parameter.id,
                'date_from': date(2021, 1, 1),
            })
