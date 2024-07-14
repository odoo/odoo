# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields
from odoo.fields import Datetime
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


def _generate_payslips(env):
    # Do this only when demo data is activated
    if env.ref('l10n_be_hr_payroll.res_company_be', raise_if_not_found=False):
        if not env['hr.payslip'].sudo().search_count([('employee_id.name', '=', 'Marian Weaver')]):
            _logger.info('Generating payslips')
            employees = env['hr.employee'].search([
                ('company_id', '=', env.ref('l10n_be_hr_payroll.res_company_be').id),
                ('id', '!=', env.ref('test_l10n_be_hr_payroll_account.hr_employee_joseph_noluck').id),
            ])
            # Everyone was on training 1 week
            leaves = env['hr.leave']
            training_type = env.ref('test_l10n_be_hr_payroll_account.l10n_be_leave_type_training')
            for employee in employees:
                training_leave = env['hr.leave'].new({
                    'name': 'Whole Company Training',
                    'employee_id': employee.id,
                    'holiday_status_id': training_type.id,
                    'request_date_from': fields.Date.today() + relativedelta(day=1, month=1, years=-1),
                    'request_date_to': fields.Date.today() + relativedelta(day=7, month=1, years=-1),
                    'request_hour_from': '7',
                    'request_hour_to': '18',
                    'number_of_days': 5,
                })
                training_leave._compute_date_from_to()
                leaves |= env['hr.leave'].create(training_leave._convert_to_write(training_leave._cache))
            env['hr.leave'].search([]).write({'payslip_state': 'done'})  # done or normal : to check!!!

            wizard_vals = {
                'employee_ids': [(4, employee.id) for employee in employees],
                'structure_id': env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id
            }
            cids = env.ref('l10n_be_hr_payroll.res_company_be').ids
            payslip_runs = env['hr.payslip.run']
            payslis_values = []
            for i in range(2, 20):
                date_start = Datetime.today() - relativedelta(months=i, day=1)
                date_end = Datetime.today() - relativedelta(months=i, day=31)
                payslis_values.append({
                    'name': date_start.strftime('%B %Y'),
                    'date_start': date_start,
                    'date_end': date_end,
                    'company_id': env.ref('l10n_be_hr_payroll.res_company_be').id,
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

        # Generate skills logs
        logs_vals = []
        data_vals = []
        today = fields.Date.today()
        all_skills = env['hr.skill'].search([])
        all_employees = env['hr.employee'].search([])
        for employee in all_employees:
            for skill in all_skills:
                for index, level in enumerate(skill.skill_type_id.skill_level_ids):
                    logs_vals.append({
                        'employee_id': employee.id,
                        'department_id': employee.department_id.id,
                        'skill_id': skill.id,
                        'skill_type_id': skill.skill_type_id.id,
                        'skill_level_id': level.id,
                        'date': today - relativedelta(months=(index + 1) * 3 + index % 3)
                    })
        skill_logs = env['hr.employee.skill.log'].create(logs_vals)
        prefix = 'test_l10n_be_hr_payroll_account'
        for log in skill_logs:
            employee_id = log.employee_id.id
            skill_id = log.skill_id.id
            level_id = log.skill_level_id.id
            data_vals.append({
                'name': f'{prefix}.skill_log_employee_{employee_id}_skill_{skill_id}_level_{level_id}',
                'module': prefix,
                'res_id': log.id,
                'model': 'hr.employee.skill.log',
                'noupdate': True,
            })
        env['ir.model.data'].create(data_vals)
