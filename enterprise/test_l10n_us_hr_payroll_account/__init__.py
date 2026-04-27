# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.fields import Datetime
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


def _generate_payslips(env):
    # Do this only when demo data is activated
    if employee_maggie := env.ref('l10n_us_hr_payroll.hr_employee_maggie', raise_if_not_found=False):
        if not env['hr.payslip'].sudo().search_count([('employee_id.name', '=', 'Maggie Davidson (mda)')]):
            _logger.info('Generating payslips')
            wizard_vals = {
                'employee_ids': [(4, employee_maggie.id)],
                'structure_id': env.ref('l10n_us_hr_payroll.hr_payroll_structure_us_employee_salary').id
            }
            cids = env.ref('base.main_company').ids
            payslip_runs = env['hr.payslip.run']
            payslis_values = []
            for i in range(1, 13):
                date_start = Datetime.today() - relativedelta(months=i, day=1)
                date_end = Datetime.today() - relativedelta(months=i, day=31)
                if date_start.year < 2023:
                    continue
                payslis_values.append({
                    'name': date_start.strftime('%B %Y'),
                    'date_start': date_start,
                    'date_end': date_end,
                    'company_id': env.ref('base.main_company').id,
                })
            payslip_runs = env['hr.payslip.run'].create(payslis_values)
            for payslip_run in payslip_runs:
                wizard = env['hr.payslip.employees'].create(wizard_vals)
                wizard.with_context(active_id=payslip_run.id, allowed_company_ids=cids).compute_sheet()
            _logger.info('Validating payslips')
            # after many insertions in work_entries, table statistics may be broken.
            # In this case, query plan may be randomly suboptimal leading to slow search
            # Analyzing the table is fast, and will transform a potential ~30 seconds
            # sql time for _mark_conflicting_work_entries into ~2 seconds
            env.cr.execute('ANALYZE hr_work_entry')
            payslip_runs.with_context(allowed_company_ids=cids).action_validate()
