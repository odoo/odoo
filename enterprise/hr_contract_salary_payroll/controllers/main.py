# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time

from odoo import _
from odoo.addons.hr_contract_salary.controllers import main
from odoo.http import route, request
from odoo.tools.float_utils import float_compare


class HrContractSalary(main.HrContractSalary):

    def _get_new_contract_values(self, contract, employee, advantages, offer):
        contract_vals = super()._get_new_contract_values(contract, employee, advantages, offer)
        contract_vals['work_entry_source'] = contract.work_entry_source
        contract_vals['standard_calendar_id'] = contract.standard_calendar_id.id
        if contract.wage_type == 'hourly':
            contract_vals['hourly_wage'] = contract.hourly_wage
        return contract_vals

    def _generate_payslip(self, new_contract):
        return request.env['hr.payslip'].sudo().create({
            'employee_id': new_contract.employee_id.id,
            'contract_id': new_contract.id,
            'struct_id': new_contract.structure_type_id.default_struct_id.id,
            'company_id': new_contract.employee_id.company_id.id,
            'name': 'Payslip Simulation',
        })

    def _get_payslip_line_values(self, payslip, codes):
        return payslip._get_line_values(codes)

    def _get_compute_results(self, new_contract):
        schedule_pay_label = dict(request.env['hr.contract']._fields['schedule_pay']._description_selection(request.env))

        def _get_period_name(category_id, contract):
            if category_id == request.env.ref("hr_contract_salary.hr_contract_salary_resume_category_monthly_salary"):
                period_name = schedule_pay_label.get(contract.schedule_pay, "Monthly")
                return f"{period_name} Salary"
            return category_id.name

        result = super()._get_compute_results(new_contract)

        # generate a payslip corresponding to only this contract
        payslip = self._generate_payslip(new_contract)

        # For hourly wage contracts generate the worked_days_line_ids manually
        if new_contract.wage_type == 'hourly':
            work_days_data = new_contract.employee_id._get_work_days_data_batch(
                datetime.combine(payslip.date_from, time.min), datetime.combine(payslip.date_to, time.max),
                compute_leaves=False, calendar=new_contract.resource_calendar_id,
            )[new_contract.employee_id.id]
            payslip.worked_days_line_ids = request.env['hr.payslip.worked_days'].with_context(salary_simulation=True).sudo().create({
                'payslip_id': payslip.id,
                'work_entry_type_id': new_contract._get_default_work_entry_type_id(),
                'number_of_days': work_days_data.get('days', 0),
                'number_of_hours': work_days_data.get('hours', 0),
            })

        # Part Time Simulation
        working_schedule = new_contract.env.context.get("simulation_working_schedule", '100')
        old_calendar = payslip.contract_id.company_id.resource_calendar_id
        old_wage_on_payroll = payslip.contract_id.wage_on_signature
        old_wage = payslip.contract_id.wage

        if working_schedule == '100':
            pass
        elif working_schedule == '90':
            new_calendar = old_calendar.copy({'global_leave_ids': False})
            if not new_calendar.two_weeks_calendar:
                new_calendar.switch_calendar_type()
            new_calendar.attendance_ids.filtered(lambda a: a.day_period != 'lunch')[:2].unlink()
        elif working_schedule == '80':
            new_calendar = old_calendar.copy({'global_leave_ids': False})
            if new_calendar.two_weeks_calendar:
                new_calendar.switch_calendar_type()
            new_calendar.attendance_ids.filtered(lambda a: a.day_period != 'lunch')[:2].unlink()
        elif working_schedule == '60':
            new_calendar = old_calendar.copy({'global_leave_ids': False})
            if new_calendar.two_weeks_calendar:
                new_calendar.switch_calendar_type()
            new_calendar.attendance_ids.filtered(lambda a: a.day_period != 'lunch')[:4].unlink()
        elif working_schedule == '50':
            new_calendar = old_calendar.copy({'global_leave_ids': False})
            if new_calendar.two_weeks_calendar:
                new_calendar.switch_calendar_type()
            new_calendar.attendance_ids.filtered(lambda a: a.day_period != 'lunch')[:5].unlink()
        elif working_schedule == '40':
            new_calendar = old_calendar.copy({'global_leave_ids': False})
            if new_calendar.two_weeks_calendar:
                new_calendar.switch_calendar_type()
            new_calendar.attendance_ids.filtered(lambda a: a.day_period != 'lunch')[:6].unlink()
        elif working_schedule == '20':
            new_calendar = old_calendar.copy({'global_leave_ids': False})
            if new_calendar.two_weeks_calendar:
                new_calendar.switch_calendar_type()
            new_calendar.attendance_ids.filtered(lambda a: a.day_period != 'lunch')[:8].unlink()
        new_wage_on_payroll = old_wage_on_payroll * int(working_schedule) / 100.0
        new_wage = old_wage * int(working_schedule) / 100.0

        payslip = payslip.with_context(
            salary_simulation=True,
            salary_simulation_full_time=working_schedule == '100',
            origin_contract_id=new_contract.env.context['origin_contract_id'],
            lang=None
        )
        if working_schedule != '100':
            payslip.contract_id.write({
                'resource_calendar_id': new_calendar.id,
                'wage_on_signature': new_wage_on_payroll,
                'wage': new_wage,
            })
        payslip.compute_sheet()

        result['payslip_lines'] = [(
            line.name,
            abs(round(line.total, 2)),
            line.code,
            'no_sign' if line.code in ['BASIC', 'SALARY', 'GROSS', 'NET'] else float_compare(line.total, 0, precision_digits=2),
            new_contract.company_id.currency_id.position,
            new_contract.company_id.currency_id.symbol
        ) for line in payslip.line_ids.filtered(lambda l: l.appears_on_payslip)]
        # Allowed company ids might not be filled or request.env.user.company_ids might be wrong
        # since we are in route context, force the company to make sure we load everything
        resume_lines = request.env['hr.contract.salary.resume'].sudo().with_company(new_contract.company_id).search([
            '|',
            ('structure_type_id', '=', False),
            ('structure_type_id', '=', new_contract.structure_type_id.id),
            ('value_type', 'in', ['payslip', 'monthly_total'])])
        monthly_total = 0
        monthly_total_lines = resume_lines.filtered(lambda l: l.value_type == 'monthly_total')

        # new categories could be introduced at this step
        # recreate resume_categories
        resume_categories = request.env['hr.contract.salary.resume'].sudo().with_company(new_contract.company_id).search([
            '|', '&', '|',
                    ('structure_type_id', '=', False),
                    ('structure_type_id', '=', new_contract.structure_type_id.id),
                ('value_type', 'in', ['fixed', 'contract', 'monthly_total', 'sum']),
            ('id', 'in', resume_lines.ids)]).category_id
        result['resume_categories'] = [_get_period_name(c, new_contract) for c in sorted(resume_categories, key=lambda x: x.sequence)]

        all_codes = (resume_lines - monthly_total_lines).mapped('code')
        line_values = self._get_payslip_line_values(payslip, all_codes) if all_codes else False

        for resume_line in resume_lines - monthly_total_lines:
            value = round(line_values[resume_line.code][payslip.id]['total'], 2)
            resume_explanation = False
            if resume_line.code == 'GROSS' and new_contract.wage_type == 'hourly':
                resume_explanation = _('This is the gross calculated for the current month with a total of %s hours.', work_days_data.get('hours', 0))
            result['resume_lines_mapped'][_get_period_name(resume_line.category_id, new_contract)][resume_line.code] = (resume_line.name, value, new_contract.company_id.currency_id.symbol, resume_explanation, new_contract.company_id.currency_id.position, resume_line.uom)
            if resume_line.impacts_monthly_total:
                monthly_total += value / 12.0 if resume_line.category_id.periodicity == 'yearly' else value

        for resume_line in monthly_total_lines:
            super_line = result['resume_lines_mapped'][_get_period_name(resume_line.category_id, new_contract)][resume_line.code]
            line_name = super_line[0]
            if resume_line.category_id == request.env.ref("hr_contract_salary.hr_contract_salary_resume_category_total"):
                period_name = schedule_pay_label.get(new_contract.schedule_pay, "Monthly")
                line_name = f"{period_name} Equivalent"
            new_value = (line_name, round(super_line[1] + float(monthly_total), 2), super_line[2], False, new_contract.company_id.currency_id.position, resume_line.uom)
            result['resume_lines_mapped'][_get_period_name(resume_line.category_id, new_contract)][resume_line.code] = new_value

        if working_schedule != '100':
            payslip.contract_id.write({
                'resource_calendar_id': old_calendar.id,
                'wage_on_signature': old_wage_on_payroll,
                'wage': old_wage,
            })
        return result
