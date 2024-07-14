#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from pytz import timezone
from dateutil.relativedelta import relativedelta, MO, SU
from dateutil import rrule
from collections import defaultdict
from datetime import date, datetime, timedelta
from odoo import api, models, fields, _
from odoo.tools import float_round, date_utils, ormcache
from odoo.exceptions import UserError


class Payslip(models.Model):
    _inherit = 'hr.payslip'

    meal_voucher_count = fields.Integer(
        compute='_compute_work_entry_dependent_benefits')  # Overrides compute method
    private_car_missing_days = fields.Integer(
        string='Days Not Granting Private Car Reimbursement',
        compute='_compute_work_entry_dependent_benefits')
    representation_fees_missing_days = fields.Integer(
        string='Days Not Granting Representation Fees',
        compute='_compute_work_entry_dependent_benefits')
    l10n_be_is_double_pay = fields.Boolean(compute='_compute_l10n_be_is_double_pay')
    l10n_be_max_seizable_amount = fields.Float(compute='_compute_l10n_be_max_seizable_amount')
    l10n_be_max_seizable_warning = fields.Char(compute='_compute_l10n_be_max_seizable_amount')
    l10n_be_is_december = fields.Boolean(compute='_compute_l10n_be_is_december')
    l10n_be_has_eco_vouchers = fields.Boolean(compute='_compute_l10n_be_has_eco_vouchers', search='_search_l10n_be_has_eco_vouchers')

    @api.depends('employee_id', 'contract_id', 'struct_id', 'date_from', 'date_to')
    def _compute_input_line_ids(self):
        res = super()._compute_input_line_ids()
        for slip in self:
            if not slip.employee_id or not slip.date_from or not slip.date_to:
                continue
            if slip.struct_id.code == 'CP200WARRANT':
                months = relativedelta(date_utils.add(slip.date_to, days=1), slip.date_from).months
                if slip.employee_id.id in self.env.context.get('commission_real_values', {}):
                    warrant_value = self.env.context['commission_real_values'][slip.employee_id.id]
                else:
                    warrant_value = slip.contract_id.commission_on_target * months
                warrant_type = self.env.ref('l10n_be_hr_payroll.cp200_other_input_warrant')
                lines_to_remove = slip.input_line_ids.filtered(lambda x: x.input_type_id == warrant_type)
                to_remove_vals = [(3, line.id, False) for line in lines_to_remove]
                to_add_vals = [(0, 0, {
                    'amount': warrant_value,
                    'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_warrant').id
                })]
                input_line_vals = to_remove_vals + to_add_vals
                slip.update({'input_line_ids': input_line_vals})
            # If a double holiday pay should be recovered
            elif slip.struct_id.code == 'CP200DOUBLE':
                to_recover = slip._get_sum_european_time_off_days()
                if to_recover:
                    european_type = self.env.ref('l10n_be_hr_payroll.input_double_holiday_european_leave_deduction')
                    lines_to_remove = slip.input_line_ids.filtered(lambda x: x.input_type_id == european_type)
                    to_remove_vals = [(3, line.id, False) for line in lines_to_remove]
                    to_add_vals = [(0, 0, {
                        'name': _('European Leaves Deduction'),
                        'amount': to_recover,
                        'input_type_id': european_type.id,
                    })]
                    slip.write({'input_line_ids': to_remove_vals + to_add_vals})
        return res

    @ormcache('self.employee_id', 'self.date_from', 'self.date_to')
    def _get_period_contracts(self):
        # Returns all the employee contracts over the same payslip period, to avoid
        # double remunerations for some line codes
        self.ensure_one()
        if self.env.context.get('salary_simulation'):
            return self.env.context['origin_contract_id']
        contracts = self.employee_id._get_contracts(
            self.date_from,
            self.date_to,
            states=['open', 'close']
        ).sorted('date_start')
        return contracts.ids

    @api.depends('worked_days_line_ids.number_of_hours', 'worked_days_line_ids.is_paid', 'worked_days_line_ids.is_credit_time')
    def _compute_worked_hours(self):
        super()._compute_worked_hours()
        for payslip in self:
            payslip.sum_worked_hours -= sum([line.number_of_hours for line in payslip.worked_days_line_ids if line.is_credit_time])

    @api.depends('struct_id', 'date_from')
    def _compute_l10n_be_is_december(self):
        for payslip in self:
            payslip.l10n_be_is_december = payslip.struct_id.code == "CP200MONTHLY" and payslip.date_from and payslip.date_from.month == 12

    def _compute_work_entry_dependent_benefits(self):
        if self.env.context.get('salary_simulation'):
            for payslip in self:
                payslip.meal_voucher_count = 20
                payslip.private_car_missing_days = 0
                payslip.representation_fees_missing_days = 0
        else:
            all_benefits = self.env['hr.work.entry.type'].get_work_entry_type_benefits()
            query = self.env['l10n_be.work.entry.daily.benefit.report']._search([
                ('employee_id', 'in', self.mapped('employee_id').ids),
                ('day', '<=', max(self.mapped('date_to'))),
                ('day', '>=', min(self.mapped('date_from'))),
            ])
            query_str, params = query.select('day', 'benefit_name', 'employee_id')
            self.env.cr.execute(query_str, params)
            work_entries_benefits_rights = self.env.cr.dictfetchall()

            work_entries_benefits_rights_by_employee = defaultdict(list)
            for work_entries_benefits_right in work_entries_benefits_rights:
                employee_id = work_entries_benefits_right['employee_id']
                work_entries_benefits_rights_by_employee[employee_id].append(work_entries_benefits_right)

            # {(calendar, date_from, date_to): resources}
            mapped_resources = defaultdict(lambda: self.env['resource.resource'])
            for payslip in self:
                contract = payslip.contract_id
                calendar = contract.resource_calendar_id if not contract.time_credit else contract.standard_calendar_id
                mapped_resources[(calendar, payslip.date_from, payslip.date_to)] |= contract.employee_id.resource_id
            # {(calendar, date_from, date_to): intervals}}
            mapped_intervals = {}
            for (calendar, date_from, date_to), resources in mapped_resources.items():
                tz = timezone(calendar.tz)
                mapped_intervals[(calendar, date_from, date_to)] = calendar._attendance_intervals_batch(
                    tz.localize(fields.Datetime.to_datetime(date_from)),
                    tz.localize(fields.Datetime.to_datetime(date_to) + timedelta(days=1, seconds=-1)),
                    resources=resources, tz=tz)

            for payslip in self:
                contract = payslip.contract_id
                benefits = dict.fromkeys(all_benefits, 0)
                date_from = max(payslip.date_from, contract.date_start)
                date_to = min(payslip.date_to, contract.date_end or payslip.date_to)
                for work_entries_benefits_right in (
                        work_entries_benefits_right
                        for work_entries_benefits_right in work_entries_benefits_rights_by_employee[payslip.employee_id.id]
                        if date_from <= work_entries_benefits_right['day'] <= date_to
                    ):
                    if work_entries_benefits_right['benefit_name'] not in benefits:
                        benefits[work_entries_benefits_right['benefit_name']] = 1
                    else:
                        benefits[work_entries_benefits_right['benefit_name']] += 1

                contract = payslip.contract_id
                resource = contract.employee_id.resource_id
                calendar = contract.resource_calendar_id if not contract.time_credit else contract.standard_calendar_id
                intervals = mapped_intervals[(calendar, payslip.date_from, payslip.date_to)][resource.id]

                nb_of_days_to_work = len({dt_from.date(): True for (dt_from, dt_to, attendance) in intervals})
                payslip.private_car_missing_days = nb_of_days_to_work - (benefits['private_car'] if 'private_car' in benefits else 0)
                payslip.representation_fees_missing_days = nb_of_days_to_work - (benefits['representation_fees'] if 'representation_fees' in benefits else 0)
                payslip.meal_voucher_count = benefits['meal_voucher']

    @api.depends('struct_id')
    def _compute_l10n_be_is_double_pay(self):
        for payslip in self:
            payslip.l10n_be_is_double_pay = payslip.struct_id.code == "CP200DOUBLE"

    @api.depends('input_line_ids')
    def _compute_l10n_be_has_eco_vouchers(self):
        for slip in self:
            slip.l10n_be_has_eco_vouchers = any(input_line.code == 'ECOVOUCHERS' for input_line in slip.input_line_ids)

    def _search_l10n_be_has_eco_vouchers(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise UserError(_('Operation not supported'))
        if operator != '=':
            value = not value
        self._cr.execute("""
            SELECT id
            FROM hr_payslip payslip
            WHERE EXISTS
                (SELECT 1
                 FROM   hr_payslip_input hpi
                 JOIN   hr_payslip_input_type hpit
                 ON     hpi.input_type_id = hpit.id AND hpit.code = 'ECOVOUCHERS'
                 WHERE  hpi.payslip_id = payslip.id
                 LIMIT  1)
        """)
        return [('id', 'in' if value else 'not in', [r[0] for r in self._cr.fetchall()])]

    @api.depends('struct_id')
    def _compute_contract_domain_ids(self):
        reimbursement_payslips = self.filtered(lambda p: p.struct_id.code == "CP200REIMBURSEMENT")
        for payslip in reimbursement_payslips:
            payslip.contract_domain_ids = self.env['hr.contract'].search([
                ('company_id', '=', payslip.company_id.id),
                ('employee_id', '=', payslip.employee_id.id),
                ('state', '!=', 'cancel')])
        super(Payslip, self - reimbursement_payslips)._compute_contract_domain_ids()

    @api.depends('date_to', 'line_ids.total', 'input_line_ids.code')
    def _compute_l10n_be_max_seizable_amount(self):
        # Source: https://emploi.belgique.be/fr/themes/remuneration/protection-de-la-remuneration/saisie-et-cession-sur-salaires
        all_payslips = self.env['hr.payslip'].search([
            ('employee_id', 'in', self.employee_id.ids),
            ('state', '!=', 'cancel')])
        payslip_values = all_payslips._get_line_values(['NET'])
        for payslip in self:
            if payslip.struct_id.country_id.code != 'BE':
                payslip.l10n_be_max_seizable_amount = 0
                payslip.l10n_be_max_seizable_warning = False
                continue

            rates = self.env['hr.rule.parameter']._get_parameter_from_code('cp200_seizable_percentages', payslip.date_to, raise_if_not_found=False)
            child_increase = self.env['hr.rule.parameter']._get_parameter_from_code('cp200_seizable_amount_child', payslip.date_to, raise_if_not_found=False)
            if not rates or not child_increase:
                payslip.l10n_be_max_seizable_amount = 0
                payslip.l10n_be_max_seizable_warning = False
                continue

            # Note: the ceiling amounts are based on the net revenues
            period_payslips = all_payslips.filtered(
                lambda p: p.employee_id == payslip.employee_id and p.date_from == payslip.date_from and p.date_to == payslip.date_to)
            net_amount = sum([payslip_values['NET'][p.id]['total'] for p in period_payslips])
            seized_amount = sum([period_payslips._get_input_line_amount(code) for code in ['ATTACH_SALARY', 'ASSIG_SALARY', 'CHILD_SUPPORT']])
            net_amount += seized_amount
            # Note: The reduction for dependant children is not applied most of the time because
            #       the process is too complex.
            # To benefit from this increase in the elusive or non-transferable quotas, the worker
            # whose remuneration is subject to seizure or transfer, must declare it using a form,
            # the model of which has been published in the Belgian Official Gazette. of 30 November
            # 2006.
            # He must attach to this form the documents establishing the reality of the
            # charge invoked.
            # Source: Opinion on the indexation of the amounts set in Article 1, paragraph 4, of
            # the Royal Decree of 27 December 2004 implementing Articles 1409, § 1, paragraph 4,
            # and 1409, § 1 bis, paragraph 4 , of the Judicial Code relating to the limitation of
            # seizure when there are dependent children, MB, December 13, 2019.
            dependent_children = payslip.employee_id.l10n_be_dependent_children_attachment
            max_seizable_amount = 0
            for left, right, rate in rates:
                if dependent_children:
                    left += dependent_children * child_increase
                    right += dependent_children * child_increase
                if left <= net_amount:
                    max_seizable_amount += (min(net_amount, right) - left) * rate
            payslip.l10n_be_max_seizable_amount = max_seizable_amount
            if max_seizable_amount and seized_amount > max_seizable_amount:
                payslip.l10n_be_max_seizable_warning = _('The seized amount (%s€) is above the belgian ceilings. Given a global net salary of %s€ for the pay period and %s dependent children, the maximum seizable amount is equal to %s€', round(seized_amount, 2), round(net_amount, 2), round(dependent_children, 2), round(max_seizable_amount, 2))
            else:
                payslip.l10n_be_max_seizable_warning = False

    def _get_worked_day_lines_hours_per_day(self):
        self.ensure_one()
        if self.contract_id.time_credit:
            return self.contract_id.standard_calendar_id.hours_per_day
        return super()._get_worked_day_lines_hours_per_day()

    def _get_worked_day_lines_values(self, domain=None):
        self.ensure_one()
        res = []
        if self.struct_id.country_id.code != 'BE':
            return super()._get_worked_day_lines_values(domain=domain)
        # If a belgian payslip has half-day attendances/time off, it the worked days lines should
        # be separated
        work_hours = self.contract_id._get_work_hours_split_half(self.date_from, self.date_to, domain=domain)
        work_hours_ordered = sorted(work_hours.items(), key=lambda x: x[1])
        for worked_days_data, duration_data in work_hours_ordered:
            duration_type, work_entry_type_id = worked_days_data
            number_of_days, number_of_hours = duration_data
            work_entry_type = self.env['hr.work.entry.type'].browse(work_entry_type_id)
            attendance_line = {
                'sequence': work_entry_type.sequence,
                'work_entry_type_id': work_entry_type_id,
                'number_of_days': number_of_days,
                'number_of_hours': number_of_hours,
            }
            res.append(attendance_line)
        # If there is a public holiday less than 30 days after the end of the contract
        # this public holiday should be taken into account in the worked days lines
        if self.contract_id.date_end and self.date_from <= self.contract_id.date_end <= self.date_to:
            # If the contract is followed by another one (eg. after an appraisal)
            if self.contract_id.employee_id.contract_ids.filtered(lambda c: c.state in ['open', 'close'] and c.date_start > self.contract_id.date_end):
                return res
            public_holiday_type = self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday')
            public_leaves = self.contract_id.resource_calendar_id.global_leave_ids.filtered(
                lambda l: l.work_entry_type_id == public_holiday_type)
            # If less than 15 days under contract, the public holidays is not reimbursed
            public_leaves = public_leaves.filtered(
                lambda l: (l.date_from.date() - self.employee_id.first_contract_date).days >= 15)
            # If less than 15 days of occupation -> no payment of the time off after contract
            # If less than 1 month of occupation -> payment of the time off occurring within 15 days after contract.
            # Occupation = duration since the start of the contract, from date to date
            public_leaves = public_leaves.filtered(
                lambda l: 0 < (l.date_from.date() - self.contract_id.date_end).days <= (30 if self.employee_id.first_contract_date + relativedelta(months=1) <= self.contract_id.date_end else 15))
            if public_leaves:
                input_type_id = self.env.ref('l10n_be_hr_payroll.cp200_other_input_after_contract_public_holidays').id
                if input_type_id not in self.input_line_ids.mapped('input_type_id').ids:
                    self.write({'input_line_ids': [(0, 0, {
                        'name': _('After Contract Public Holidays'),
                        'amount': 0.0,
                        'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_after_contract_public_holidays').id,
                    })]})
        # Handle loss on commissions
        if self._get_last_year_average_variable_revenues():
            we_types_ids = (
                self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday') + self.env.ref('l10n_be_hr_payroll.work_entry_type_small_unemployment')
            ).ids
            # if self.worked_days_line_ids.filtered(lambda wd: wd.code in ['LEAVE205', 'LEAVE500']):
            if any(line_vals['work_entry_type_id'] in we_types_ids for line_vals in res):
                we_type = self.env.ref('l10n_be_hr_payroll.work_entry_type_simple_holiday_pay_variable_salary')
                res.append({
                    'sequence': we_type.sequence,
                    'work_entry_type_id': we_type.id,
                    'number_of_days': 0,
                    'number_of_hours': 0,
                })
        return res

    def _get_last_year_average_variable_revenues(self):
        if not self.contract_id.commission_on_target:
            return 0
        date_from = self.env.context.get('variable_revenue_date_from', self.date_from)
        first_contract_date = self.employee_id.first_contract_date
        if not first_contract_date:
            return 0
        start = first_contract_date
        end = date_from + relativedelta(day=31, months=-1)
        number_of_month = (end.year - start.year) * 12 + (end.month - start.month) + 1
        number_of_month = min(12, number_of_month)
        if number_of_month <= 0:
            return 0
        payslips = self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', 'in', ['done', 'paid']),
            ('date_from', '>=', date_from + relativedelta(months=-12, day=1)),
            ('date_from', '<=', date_from),
        ], order="date_from asc")
        total_amount = payslips._get_line_values(['COMMISSION'], compute_sum=True)['COMMISSION']['sum']['total']
        return total_amount / number_of_month if number_of_month else 0

    def _get_last_year_average_warrant_revenues(self):
        warrant_payslips = self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', 'in', ['done', 'paid']),
            ('struct_id.code', '=', 'CP200WARRANT'),
            ('date_from', '>=', self.date_from + relativedelta(months=-12, day=1)),
            ('date_from', '<', self.date_from),
        ], order="date_from asc")
        total_amount = warrant_payslips._get_line_values(['BASIC'], compute_sum=True)['BASIC']['sum']['total']
        first_contract_date = self.employee_id.first_contract_date
        if not first_contract_date:
            return 0
        # Only complete months count
        if first_contract_date.day != 1:
            start = first_contract_date + relativedelta(day=1, months=1)
        else:
            start = first_contract_date
        end = self.date_from + relativedelta(day=31, months=-1)
        number_of_month = (end.year - start.year) * 12 + (end.month - start.month) + 1
        number_of_month = min(12, number_of_month)
        return total_amount / number_of_month if number_of_month else 0

    def _compute_number_complete_months_of_work(self, date_from, date_to, contracts):
        invalid_days_by_year = defaultdict(lambda: defaultdict(dict))
        for day in rrule.rrule(rrule.DAILY, dtstart=date_from + relativedelta(day=1), until=date_to + relativedelta(day=31)):
            invalid_days_by_year[day.year][day.month][day.date()] = True

        public_holidays = [(leave.date_from.date(), leave.date_to.date()) for leave in self.employee_id._get_public_holidays(date_from, date_to)]
        for contract in contracts:
            work_days = {int(d) for d in contract.resource_calendar_id._get_global_attendances().mapped('dayofweek')}

            previous_week_start = max(contract.date_start + relativedelta(weeks=-1, weekday=MO(-1)), date_from + relativedelta(day=1))
            next_week_end = min(contract.date_end + relativedelta(weeks=+1, weekday=SU(+1)) if contract.date_end else date.max, date_to)
            days_to_check = rrule.rrule(rrule.DAILY, dtstart=previous_week_start, until=next_week_end)
            for day in days_to_check:
                day = day.date()
                out_of_schedule = True

                # Full time credit time doesn't count
                if contract.time_credit and not contract.work_time_rate:
                    continue
                if (contract.date_start <= day <= (contract.date_end or date.max) or
                        day.weekday() not in work_days or
                        any(date_from <= day <= date_to for date_from, date_to in public_holidays)):
                    out_of_schedule = False
                invalid_days_by_year[day.year][day.month][day] &= out_of_schedule

        complete_months = [
            month
            for year, invalid_days_by_months in invalid_days_by_year.items()
            for month, days in invalid_days_by_months.items()
            if not any(days.values())
        ]
        return len(complete_months)

    def _compute_presence_prorata(self, date_from, date_to, contracts):
        unpaid_work_entry_types = self.struct_id.unpaid_work_entry_type_ids
        paid_work_entry_types = self.env['hr.work.entry.type'].search([]) - unpaid_work_entry_types
        hours = contracts.get_work_hours(date_from, date_to)
        paid_hours = sum(v for k, v in hours.items() if k in paid_work_entry_types.ids)
        unpaid_hours = sum(v for k, v in hours.items() if k in unpaid_work_entry_types.ids)
        # Take 30 unpaid sick open days as paid time off
        if self.struct_id.code == 'CP200THIRTEEN':
            unpaid_sick_codes = ['LEAVE280', 'LEAVE214']
            date_from = datetime.combine(date_from, datetime.min.time())
            date_to = datetime.combine(date_to, datetime.max.time())
            work_entries = self.env['hr.work.entry'].search([
                ('state', 'in', ['validated', 'draft']),
                ('employee_id', '=', self.employee_id.id),
                ('date_start', '>=', date_from),
                ('date_stop', '<=', date_to),
                ('work_entry_type_id.code', 'in', unpaid_sick_codes),
            ], order="date_start asc")
            days_count, valid_sick_hours = 0, 0
            valid_days = set()
            for work_entry in work_entries:
                work_entry_date = work_entry.date_start.date()
                if work_entry_date in valid_days:
                    valid_sick_hours += work_entry.duration
                elif days_count < 30:
                    valid_days.add(work_entry_date)
                    days_count += 1
                    valid_sick_hours += work_entry.duration
            paid_hours += valid_sick_hours
            unpaid_hours -= valid_sick_hours
        return paid_hours / (paid_hours + unpaid_hours) if paid_hours or unpaid_hours else 0

    def _get_paid_amount_13th_month(self):
        # Counts the number of fully worked month
        # If any day in the month is not covered by the contract dates coverage
        # the entire month is not taken into account for the proratization
        contracts = self.employee_id.contract_ids.filtered(lambda c: c.state not in ['draft', 'cancel'] and c.structure_type_id == self.struct_id.type_id)
        first_contract_date = self.contract_id.employee_id._get_first_contract_date(no_gap=False)
        if not contracts or not first_contract_date:
            return 0.0
        # Only employee with at least 6 months of XP can benefit from the 13th month bonus
        # aka employee who started before the 7th of July (to avoid issues when the month starts
        # with holidays / week-ends, etc)
        if first_contract_date.year == self.date_from.year and \
                ((first_contract_date.month == 7 and first_contract_date.day > 7) \
                or (first_contract_date.month > 7)):
            return 0.0

        date_from = max(first_contract_date, self.date_from + relativedelta(day=1, month=1))
        date_to = self.date_to + relativedelta(day=31)

        basic = self.contract_id._get_contract_wage()

        force_months = self.input_line_ids.filtered(lambda l: l.code == 'MONTHS')
        if force_months:
            n_months = force_months[0].amount
            presence_prorata = 1
        else:
            # 1. Number of months
            n_months = min(12, self._compute_number_complete_months_of_work(date_from, date_to, contracts))
            # 2. Deduct absences
            presence_prorata = self._compute_presence_prorata(date_from, date_to, contracts)

        # Could happen for contracts with gaps
        if n_months < 6:
            return 0.0

        fixed_salary = basic * n_months / 12 * presence_prorata

        force_avg_variable_revenues = self.input_line_ids.filtered(lambda l: l.code == 'VARIABLE')
        if force_avg_variable_revenues:
            avg_variable_revenues = force_avg_variable_revenues[0].amount
        else:
            if not n_months:
                avg_variable_revenues = 0
            else:
                avg_variable_revenues = self.with_context(
                    variable_revenue_date_from=self.date_from
                )._get_last_year_average_variable_revenues()
        return fixed_salary + avg_variable_revenues

    def _get_paid_amount_warrant(self):
        self.ensure_one()
        warrant_input_type = self.env.ref('l10n_be_hr_payroll.cp200_other_input_warrant')
        return sum(self.input_line_ids.filtered(lambda a: a.input_type_id == warrant_input_type).mapped('amount'))

    def _get_paid_double_holiday(self):
        self.ensure_one()
        contracts = self.employee_id.contract_ids.filtered(lambda c: c.state not in ['draft', 'cancel'] and c.structure_type_id == self.struct_id.type_id)
        if not contracts:
            return 0.0

        basic = self.contract_id._get_contract_wage()
        force_months = self.input_line_ids.filtered(lambda l: l.code == 'MONTHS')

        year = self.date_from.year - 1
        date_from = date(year, 1, 1)
        date_to = date(year, 12, 31)

        if force_months:
            n_months = force_months[0].amount
            fixed_salary = basic * n_months / 12
        else:
            # 1. Number of months
            n_months = self._compute_number_complete_months_of_work(date_from, date_to, contracts)
            # 2. Deduct absences
            presence_prorata = self._compute_presence_prorata(date_from, date_to, contracts)
            fixed_salary = basic * n_months / 12 * presence_prorata
            # 3. Previous Year occupation
            if year == int(self.employee_id.first_contract_year_n1):
                for line in self.employee_id.double_pay_line_n1_ids:
                    fixed_salary += basic * line.months_count * line.occupation_rate / 100 / 12
                    n_months += line.months_count
            elif year == int(self.employee_id.first_contract_year_n):
                for line in self.employee_id.double_pay_line_n_ids:
                    fixed_salary += basic * line.months_count * line.occupation_rate / 100 / 12
                    n_months += line.months_count

        force_avg_variable_revenues = self.input_line_ids.filtered(lambda l: l.code == 'VARIABLE')
        if force_avg_variable_revenues:
            avg_variable_revenues = force_avg_variable_revenues[0].amount
        else:
            if not n_months:
                avg_variable_revenues = 0
            else:
                avg_variable_revenues = self.with_context(
                    variable_revenue_date_from=self.date_from
                )._get_last_year_average_variable_revenues()
        return fixed_salary + avg_variable_revenues

    def _get_paid_amount(self):
        self.ensure_one()
        belgian_payslip = self.struct_id.country_id.code == "BE"
        if belgian_payslip:
            if self.struct_id.code == 'CP200THIRTEEN':
                return self._get_paid_amount_13th_month()
            if self.struct_id.code == 'CP200WARRANT':
                return self._get_paid_amount_warrant()
            if self.struct_id.code == 'CP200DOUBLE':
                return self._get_paid_double_holiday()
        return super()._get_paid_amount()

    def _is_active_belgian_languages(self):
        active_langs = self.env['res.lang'].with_context(active_test=True).search([]).mapped('code')
        return any(l in active_langs for l in ["fr_BE", "fr_FR", "nl_BE", "nl_NL", "de_BE", "de_DE"])

    def _get_sum_european_time_off_days(self, check=False):
        self.ensure_one()
        two_years_payslips = self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date_to', '<=', date(self.date_from.year, 12, 31)),
            ('date_from', '>=', date(self.date_from.year - 2, 1, 1)),
            ('state', 'in', ['done', 'paid']),
        ])
        european_time_off_amount = two_years_payslips.filtered(lambda p: p.date_from.year < self.date_from.year)._get_worked_days_line_amount('LEAVE216')
        already_recovered_amount = two_years_payslips._get_line_values(['EU.LEAVE.DEDUC'], compute_sum=True)['EU.LEAVE.DEDUC']['sum']['total']
        return european_time_off_amount + already_recovered_amount

    def _is_invalid(self):
        invalid = super()._is_invalid()
        if not invalid and self._is_active_belgian_languages():
            country = self.struct_id.country_id
            if country.code == 'BE' and self.employee_id.lang not in ["fr_BE", "fr_FR", "nl_BE", "nl_NL", "de_BE", "de_DE"]:
                return _('This document is a translation. This is not a legal document.')
        return invalid

    def _get_negative_net_input_type(self):
        self.ensure_one()
        if self.struct_id.code == 'CP200MONTHLY':
            return self.env.ref('l10n_be_hr_payroll.input_negative_net')
        return super()._get_negative_net_input_type()

    def action_payslip_done(self):
        if self._is_active_belgian_languages():
            bad_language_slips = self.filtered(
                lambda p: p.struct_id.country_id.code == "BE" and p.employee_id.lang not in ["fr_BE", "fr_FR", "nl_BE", "nl_NL", "de_BE", "de_DE"])
            if bad_language_slips:
                action = self.env['ir.actions.act_window'].\
                    _for_xml_id('l10n_be_hr_payroll.l10n_be_hr_payroll_employee_lang_wizard_action')
                ctx = dict(self.env.context)
                ctx.update({
                    'employee_ids': bad_language_slips.employee_id.ids,
                    'default_slip_ids': self.ids,
                })
                action['context'] = ctx
                return action
        return super().action_payslip_done()

    def _get_pdf_reports(self):
        res = super()._get_pdf_reports()
        report_n = self.env.ref('l10n_be_hr_payroll.action_report_termination_holidays_n')
        report_n1 = self.env.ref('l10n_be_hr_payroll.action_report_termination_holidays_n1')
        for payslip in self:
            if payslip.struct_id.code == 'CP200HOLN1':
                res[report_n1] |= payslip
            elif payslip.struct_id.code == 'CP200HOLN':
                res[report_n] |= payslip
        return res

    def _get_data_files_to_update(self):
        # Note: file order should be maintained
        return super()._get_data_files_to_update() + [(
            'l10n_be_hr_payroll', [
                'data/hr_rule_parameters_data.xml',
            ])]

    def _get_dashboard_warnings(self):
        res = super()._get_dashboard_warnings()
        belgian_companies = self.env.companies.filtered(lambda c: c.country_id.code == 'BE')
        if belgian_companies:
            # NISS VALIDATION
            invalid_niss_employee_ids = self.env['hr.employee']._get_invalid_niss_employee_ids()
            if invalid_niss_employee_ids:
                invalid_niss_str = _('Employees With Invalid NISS Numbers')
                res.append({
                    'string': invalid_niss_str,
                    'count': len(invalid_niss_employee_ids),
                    'action': self._dashboard_default_action(invalid_niss_str, 'hr.employee', invalid_niss_employee_ids),
                })

            # GENDER VALIDATION
            invalid_gender_employees = self.env['hr.employee'].search([
                ('gender', 'not in', ['male', 'female']),
                ('company_id', 'in', belgian_companies.ids)
            ])
            if invalid_gender_employees:
                invalid_gender_str = _('Employees With Invalid Configured Gender')
                res.append({
                    'string': invalid_gender_str,
                    'count': len(invalid_gender_employees),
                    'action': self._dashboard_default_action(invalid_gender_str, 'hr.employee', invalid_gender_employees.ids),
                })

            # LANGUAGE VALIDATION
            active_languages = self._is_active_belgian_languages()
            if active_languages:
                invalid_language_employees = self.env['hr.employee'].search([
                    ('company_id', 'in', belgian_companies.ids)
                ]).filtered(lambda e: e.lang not in ["fr_BE", "fr_FR", "nl_BE", "nl_NL", "de_BE", "de_DE"])
            else:
                invalid_language_employees = self.env['hr.employee']
            if invalid_language_employees:
                invalid_gender_str = _('Employees With Invalid Configured Language')
                res.append({
                    'string': invalid_gender_str,
                    'count': len(invalid_language_employees),
                    'action': self._dashboard_default_action(invalid_gender_str, 'hr.employee', invalid_language_employees.ids),
                })

            # WORK ADDRESS VALIDATION
            address_employees = self.env['hr.employee'].search([
                ('company_id', 'in', belgian_companies.ids),
                ('employee_type', 'in', ['employee', 'student']),
                ('contract_id.state', 'in', ['open', 'close']),
            ])
            work_addresses = address_employees.mapped('address_id')
            location_units = self.env['l10n_be.dmfa.location.unit'].search([('partner_id', 'in', work_addresses.ids)])
            invalid_addresses = work_addresses - location_units.mapped('partner_id')
            if invalid_addresses:
                invalid_address_str = _('Work addresses without ONSS identification code')
                res.append({
                    'string': invalid_address_str,
                    'count': len(invalid_addresses),
                    'action': self._dashboard_default_action(invalid_address_str, 'res.partner', invalid_addresses.ids),
                })

            # SICK MORE THAN 30 DAYS
            sick_work_entry_type = self.env.ref('hr_work_entry_contract.work_entry_type_sick_leave')
            partial_sick_work_entry_type = self.env.ref('l10n_be_hr_payroll.work_entry_type_part_sick')
            long_sick_work_entry_type = self.env.ref('l10n_be_hr_payroll.work_entry_type_long_sick')
            sick_work_entry_types = sick_work_entry_type + partial_sick_work_entry_type + long_sick_work_entry_type

            sick_more_than_30days_leave = self.env['hr.leave'].search([
                ('employee_company_id', '=', self.env.company.id),
                ('date_from', '<=', date.today() + relativedelta(days=-31)),
                ('holiday_status_id.work_entry_type_id', 'in', sick_work_entry_types.ids),
                ('state', '=', 'validate'),
            ])

            employees_on_long_sick_leave = []
            employee_ids = sick_more_than_30days_leave.mapped('employee_id').ids
            for employee_id in employee_ids:
                employee_leaves = sick_more_than_30days_leave.filtered(lambda l: l.employee_id.id == employee_id)
                total_duration = sum([(leave.date_to - leave.date_from).days for leave in employee_leaves])
                if total_duration > 30:
                    employees_on_long_sick_leave.append(employee_id)

            sick_more_than_30days_str = _('Employee on Mutual Health (> 30 days Illness)')
            if employees_on_long_sick_leave:
                res.append({
                    'string': sick_more_than_30days_str,
                    'count': len(employees_on_long_sick_leave),
                    'action': self._dashboard_default_action(sick_more_than_30days_str, 'hr.employee', employees_on_long_sick_leave),
                })

        return res

    def _get_ffe_contribution_rate(self, worker_count):
        # Fond de fermeture d'entreprise
        # https://www.socialsecurity.be/employer/instructions/dmfa/fr/latest/instructions/special_contributions/other_specialcontributions/basiccontributions_closingcompanyfunds.html
        self.ensure_one()
        if self.company_id.l10n_be_ffe_employer_type == 'commercial':
            if worker_count < 20:
                rate = self.env['hr.rule.parameter']._get_parameter_from_code('l10n_be_ffe_commercial_rate_low', self.date_to)
            else:
                rate = self.env['hr.rule.parameter']._get_parameter_from_code('l10n_be_ffe_commercial_rate_high', self.date_to)
        else:
            rate = self.env['hr.rule.parameter']._get_parameter_from_code('l10n_be_ffe_noncommercial_rate', self.date_to)
        return rate

    def _get_be_termination_withholding_rate(self, localdict):
        # See: https://www.securex.eu/lex-go.nsf/vwReferencesByCategory_fr/52DA120D5DCDAE78C12584E000721081?OpenDocument
        self.ensure_one()
        def find_rates(x, rates):
            for low, high, rate in rates:
                if low <= x <= high:
                    return rate

        inputs = localdict['inputs']
        if 'ANNUAL_TAXABLE' not in inputs:
            return 0
        annual_taxable = inputs['ANNUAL_TAXABLE'].amount

        # Note: Exoneration for children in charge is managed on the salary.rule for the amount
        rates = self._rule_parameter('holiday_pay_pp_rates')
        pp_rate = find_rates(annual_taxable, rates)

        # Rate Reduction for children in charge
        children = self.employee_id.dependent_children
        children_reduction = self._rule_parameter('holiday_pay_pp_rate_reduction')
        if children and annual_taxable <= children_reduction.get(children, children_reduction[5])[1]:
            pp_rate *= (1 - children_reduction.get(children, children_reduction[5])[0] / 100.0)
        return pp_rate

    def _get_be_withholding_taxes(self, localdict):
        self.ensure_one()

        categories = localdict['categories']

        def compute_basic_bareme(value):
            rates = self._rule_parameter('basic_bareme_rates')
            rates = [(limit or float('inf'), rate) for limit, rate in rates]  # float('inf') because limit equals None for last level
            rates = sorted(rates)

            basic_bareme = 0
            previous_limit = 0
            for limit, rate in rates:
                basic_bareme += max(min(value, limit) - previous_limit, 0) * rate
                previous_limit = limit
            return float_round(basic_bareme, precision_rounding=0.01)

        def convert_to_month(value):
            return float_round(value / 12.0, precision_rounding=0.01, rounding_method='DOWN')

        employee = self.contract_id.employee_id
        # PART 1: Withholding tax amount computation
        withholding_tax_amount = 0.0

        taxable_amount = categories['GROSS']  # Base imposable

        if self.date_from.year < 2023:
            lower_bound = taxable_amount - taxable_amount % 15
        else:
            lower_bound = taxable_amount

        # yearly_gross_revenue = Revenu Annuel Brut
        yearly_gross_revenue = lower_bound * 12.0

        # yearly_net_taxable_amount = Revenu Annuel Net Imposable
        if yearly_gross_revenue <= self._rule_parameter('yearly_gross_revenue_bound_expense'):
            yearly_net_taxable_revenue = yearly_gross_revenue * (1.0 - 0.3)
        else:
            yearly_net_taxable_revenue = yearly_gross_revenue - self._rule_parameter('expense_deduction')

        # BAREME III: Non resident
        if employee.is_non_resident:
            basic_bareme = compute_basic_bareme(yearly_net_taxable_revenue)
            withholding_tax_amount = convert_to_month(basic_bareme)
        else:
            # BAREME I: Isolated or spouse with income
            if employee.marital in ['divorced', 'single', 'widower'] or (employee.marital in ['married', 'cohabitant'] and employee.spouse_fiscal_status != 'without_income'):
                basic_bareme = max(compute_basic_bareme(yearly_net_taxable_revenue) - self._rule_parameter('deduct_single_with_income'), 0.0)
                withholding_tax_amount = convert_to_month(basic_bareme)

            # BAREME II: spouse without income
            if employee.marital in ['married', 'cohabitant'] and employee.spouse_fiscal_status == 'without_income':
                yearly_net_taxable_revenue_for_spouse = min(yearly_net_taxable_revenue * 0.3, self._rule_parameter('max_spouse_income'))
                basic_bareme_1 = compute_basic_bareme(yearly_net_taxable_revenue_for_spouse)
                basic_bareme_2 = compute_basic_bareme(yearly_net_taxable_revenue - yearly_net_taxable_revenue_for_spouse)
                withholding_tax_amount = convert_to_month(max(basic_bareme_1 + basic_bareme_2 - 2 * self._rule_parameter('deduct_single_with_income'), 0))

        # Reduction for other family charges
        if (employee.children and employee.dependent_children) or (employee.other_dependent_people and (employee.dependent_seniors or employee.dependent_juniors)):
            if employee.marital in ['divorced', 'single', 'widower'] or (employee.spouse_fiscal_status != 'without_income'):

                # if employee.marital in ['divorced', 'single', 'widower']:
                #     withholding_tax_amount -= self._rule_parameter('isolated_deduction')
                if employee.marital in ['divorced', 'single', 'widower'] and employee.dependent_children:
                    withholding_tax_amount -= self._rule_parameter('disabled_dependent_deduction')
                if employee.disabled:
                    withholding_tax_amount -= self._rule_parameter('disabled_dependent_deduction')
                if employee.other_dependent_people and employee.dependent_seniors:
                    withholding_tax_amount -= self._rule_parameter('dependent_senior_deduction') * employee.dependent_seniors
                if employee.other_dependent_people and employee.dependent_juniors:
                    withholding_tax_amount -= self._rule_parameter('disabled_dependent_deduction') * employee.dependent_juniors
                if employee.marital in ['married', 'cohabitant'] and employee.spouse_fiscal_status == 'low_income':
                    withholding_tax_amount -= self._rule_parameter('spouse_low_income_deduction')
                if employee.marital in ['married', 'cohabitant'] and employee.spouse_fiscal_status == 'low_pension':
                    withholding_tax_amount -= self._rule_parameter('spouse_other_income_deduction')
            if employee.marital in ['married', 'cohabitant'] and employee.spouse_fiscal_status == 'without_income':
                if employee.disabled:
                    withholding_tax_amount -= self._rule_parameter('disabled_dependent_deduction')
                if employee.disabled_spouse_bool:
                    withholding_tax_amount -= self._rule_parameter('disabled_dependent_deduction')
                if employee.other_dependent_people and employee.dependent_seniors:
                    withholding_tax_amount -= self._rule_parameter('dependent_senior_deduction') * employee.dependent_seniors
                if employee.other_dependent_people and employee.dependent_juniors:
                    withholding_tax_amount -= self._rule_parameter('disabled_dependent_deduction') * employee.dependent_juniors

        # Child Allowances
        n_children = employee.dependent_children
        if n_children > 0:
            children_deduction = self._rule_parameter('dependent_basic_children_deduction')
            if n_children <= 8:
                withholding_tax_amount -= children_deduction.get(n_children, 0.0)
            if n_children > 8:
                withholding_tax_amount -= children_deduction.get(8, 0.0) + (n_children - 8) * self._rule_parameter('dependent_children_deduction')

        if self.contract_id.fiscal_voluntarism:
            voluntary_amount = categories['GROSS'] * self.contract_id.fiscal_voluntary_rate / 100
            if voluntary_amount > withholding_tax_amount:
                withholding_tax_amount = voluntary_amount

        return - max(withholding_tax_amount, 0.0)

    def _get_be_special_social_cotisations(self, localdict):
        self.ensure_one()

        def find_rate(x, rates):
            for low, high, rate, basis, min_amount, max_amount in rates:
                if low <= x <= high:
                    return low, high, rate, basis, min_amount, max_amount
            return 0, 0, 0, 0, 0, 0

        categories = localdict['categories']
        employee = self.contract_id.employee_id
        wage = categories['BASIC']
        if not wage or employee.is_non_resident:
            return 0.0

        if employee.marital in ['divorced', 'single', 'widower'] or (employee.marital in ['married', 'cohabitant'] and employee.spouse_fiscal_status == 'without_income'):
            rates = self._rule_parameter('cp200_monss_isolated')
            if not rates:
                rates = [
                    (0.00, 1945.38, 0.00, 0.00, 0.00, 0.00),
                    (1945.39, 2190.18, 0.076, 0.00, 0.00, 18.60),
                    (2190.19, 6038.82, 0.011, 18.60, 0.00, 60.94),
                    (6038.83, 999999999.00, 1.000, 60.94, 0.00, 60.94),
                ]
            low, dummy, rate, basis, min_amount, max_amount = find_rate(wage, rates)
            return -min(max(basis + (wage - low + 0.01) * rate, min_amount), max_amount)

        if employee.marital in ['married', 'cohabitant'] and employee.spouse_fiscal_status != 'without_income':
            rates = self._rule_parameter('cp200_monss_couple')
            if not rates:
                rates = [
                    (0.00, 1095.09, 0.00, 0.00, 0.00, 0.00),
                    (1095.10, 1945.38, 0.00, 9.30, 9.30, 9.30),
                    (1945.39, 2190.18, 0.076, 0.00, 9.30, 18.60),
                    (2190.19, 6038.82, 0.011, 18.60, 0.00, 51.64),
                    (6038.83, 999999999.00, 1.000, 51.64, 51.64, 51.64),
                ]
            low, dummy, rate, basis, min_amount, max_amount = find_rate(wage, rates)
            if isinstance(max_amount, tuple):
                if employee.spouse_fiscal_status in ['high_income', 'low_income']:
                    # conjoint avec revenus professionnels
                    max_amount = max_amount[0]
                else:
                    # conjoint sans revenus professionnels
                    max_amount = max_amount[1]
            return -min(max(basis + (wage - low + 0.01) * rate, min_amount), max_amount)
        return 0.0

    def _get_be_ip(self, localdict):
        self.ensure_one()
        contract = self.contract_id
        if not contract.ip:
            return 0.0
        return self._get_paid_amount() * contract.ip_wage_rate / 100.0

    def _get_be_ip_deduction(self, localdict):
        self.ensure_one()
        tax_rate = 0.15
        ip_amount = self._get_be_ip(localdict)
        if not ip_amount:
            return 0.0
        ip_deduction_bracket_1 = self._rule_parameter('ip_deduction_bracket_1')
        ip_deduction_bracket_2 = self._rule_parameter('ip_deduction_bracket_2')
        if 0.0 <= ip_amount <= ip_deduction_bracket_1:
            tax_rate = tax_rate / 2.0
        elif ip_deduction_bracket_1 < ip_amount <= ip_deduction_bracket_2:
            tax_rate = tax_rate * 3.0 / 4.0
        return - min(ip_amount * tax_rate, 11745)

    def _get_employment_bonus_employees_volet_A(self, localdict):
        categories = localdict['categories']
        if not self.worked_days_line_ids and not self.env.context.get('salary_simulation'):
            return 0

        # S = (W / H) * U
        # W = salaire brut
        # H = le nombre d'heures de travail déclarées avec un code prestations 1, 3, 4, 5 et 20;
        # U = le nombre maximum d'heures de prestations pour le mois concerné dans le régime de travail concerné
        if self.env.context.get('salary_simulation'):
            paid_hours = 1
            total_hours = 1
        else:
            worked_days = self.worked_days_line_ids.filtered(lambda wd: wd.code not in ['LEAVE300', 'LEAVE301'])
            paid_hours = sum(worked_days.filtered(lambda wd: wd.amount).mapped('number_of_hours'))  # H
            total_hours = sum(worked_days.mapped('number_of_hours'))  # U

        # 1. - Détermination du salaire mensuel de référence (S)
        salary = categories['BRUT'] * total_hours / paid_hours  # S = (W/H) x U

        # 2. - Détermination du montant de base de la réduction (R)
        bonus_basic_amount_volet_A = self._rule_parameter('work_bonus_basic_amount_volet_A')
        wage_lower_bound = self._rule_parameter('work_bonus_reference_wage_low')
        wage_middle_bound = self._rule_parameter('l10n_be_work_bonus_reference_wage_middle')
        wage_higher_bound = self._rule_parameter('work_bonus_reference_wage_high')
        if salary <= wage_lower_bound:
            result = bonus_basic_amount_volet_A
        elif salary <= wage_middle_bound:
            result = bonus_basic_amount_volet_A
        elif salary <= wage_higher_bound:
            coeff = self._rule_parameter('work_bonus_coeff')
            result = bonus_basic_amount_volet_A - (coeff * (salary - wage_middle_bound))
        else:
            result = 0

        # 3. - Détermination du montant de la réduction (P)
        result = result * paid_hours / total_hours  # P = (H/U) x R

        return result

    def _get_employment_bonus_employees_volet_B(self, localdict):
        categories = localdict['categories']
        if not self.worked_days_line_ids and not self.env.context.get('salary_simulation'):
            return 0

        # S = (W / H) * U
        # W = salaire brut
        # H = le nombre d'heures de travail déclarées avec un code prestations 1, 3, 4, 5 et 20;
        # U = le nombre maximum d'heures de prestations pour le mois concerné dans le régime de travail concerné
        if self.env.context.get('salary_simulation'):
            paid_hours = 1
            total_hours = 1
        else:
            worked_days = self.worked_days_line_ids.filtered(lambda wd: wd.code not in ['LEAVE300', 'LEAVE301'])
            paid_hours = sum(worked_days.filtered(lambda wd: wd.amount).mapped('number_of_hours'))  # H
            total_hours = sum(worked_days.mapped('number_of_hours'))  # U

        # 1. - Détermination du salaire mensuel de référence (S)
        salary = categories['BRUT'] * total_hours / paid_hours  # S = (W/H) x U

        # 2. - Détermination du montant de base de la réduction (R)
        bonus_basic_amount = self._rule_parameter('work_bonus_basic_amount')
        wage_lower_bound = self._rule_parameter('work_bonus_reference_wage_low')
        wage_middle_bound = self._rule_parameter('l10n_be_work_bonus_reference_wage_middle')
        wage_higher_bound = self._rule_parameter('work_bonus_reference_wage_high')
        if salary <= wage_lower_bound:
            result = bonus_basic_amount
        elif salary <= wage_middle_bound:
            coeff = self._rule_parameter('l10n_be_work_bonus_coeff_low')
            result = bonus_basic_amount - (coeff * (salary - wage_lower_bound))
        elif salary <= wage_higher_bound:
            result = 0
        else:
            result = 0

        # 3. - Détermination du montant de la réduction (P)
        result = result * paid_hours / total_hours  # P = (H/U) x R

        return result

    # ref: https://www.socialsecurity.be/employer/instructions/dmfa/fr/latest/instructions/deductions/workers_reductions/workbonus.html
    def _get_employment_bonus_employees(self, localdict):
        self.ensure_one()
        categories = localdict['categories']
        if self.date_from >= date(2024, 4, 1):
            bonus_volet_A = self._get_employment_bonus_employees_volet_A(localdict)
            bonus_volet_B = self._get_employment_bonus_employees_volet_B(localdict)
            result = bonus_volet_A + bonus_volet_B
            # Nasty lazy dev
            localdict['result_rules']['bonus_volet_A']['total'] = bonus_volet_A
            localdict['result_rules']['bonus_volet_B']['total'] = bonus_volet_B
            return min(result, -categories['ONSS'])

        bonus_basic_amount = self._rule_parameter('work_bonus_basic_amount')
        wage_lower_bound = self._rule_parameter('work_bonus_reference_wage_low')
        if not self.worked_days_line_ids and not self.env.context.get('salary_simulation'):
            return 0

        # S = (W / H) * U
        # W = salaire brut
        # H = le nombre d'heures de travail déclarées avec un code prestations 1, 3, 4, 5 et 20;
        # U = le nombre maximum d'heures de prestations pour le mois concerné dans le régime de travail concerné
        if self.env.context.get('salary_simulation'):
            paid_hours = 1
            total_hours = 1
        else:
            worked_days = self.worked_days_line_ids.filtered(lambda wd: wd.code not in ['LEAVE300', 'LEAVE301'])
            paid_hours = sum(worked_days.filtered(lambda wd: wd.amount).mapped('number_of_hours'))  # H
            total_hours = sum(worked_days.mapped('number_of_hours'))  # U

        # 1. - Détermination du salaire mensuel de référence (S)
        salary = categories['BRUT'] * total_hours / paid_hours  # S = (W/H) x U

        # 2. - Détermination du montant de base de la réduction (R)
        if self.date_from < date(2023, 7, 1):
            if salary <= wage_lower_bound:
                result = bonus_basic_amount
            elif salary <= self._rule_parameter('work_bonus_reference_wage_high'):
                coeff = self._rule_parameter('work_bonus_coeff')
                result = bonus_basic_amount - (coeff * (salary - wage_lower_bound))
            else:
                result = 0
        else:
            if salary <= wage_lower_bound:
                result = bonus_basic_amount
            elif salary <= self._rule_parameter('l10n_be_work_bonus_reference_wage_middle'):
                coeff = self._rule_parameter('l10n_be_work_bonus_coeff_low')
                result = bonus_basic_amount - (coeff * (salary - wage_lower_bound))
            elif salary <= self._rule_parameter('work_bonus_reference_wage_high'):
                coeff = self._rule_parameter('work_bonus_coeff')
                result = bonus_basic_amount - (coeff * (salary - wage_lower_bound))
            else:
                result = 0

        # 3. - Détermination du montant de la réduction (P)
        result = result * paid_hours / total_hours  # P = (H/U) x R

        return min(result, -categories['ONSS'])

    def _get_be_double_holiday_withholding_taxes(self, localdict):
        self.ensure_one()
        # See: https://www.securex.eu/lex-go.nsf/vwReferencesByCategory_fr/52DA120D5DCDAE78C12584E000721081?OpenDocument
        def find_rates(x, rates):
            for low, high, rate in rates:
                if low <= x <= high:
                    return rate / 100.0

        categories = localdict['categories']
        rates = self._rule_parameter('holiday_pay_pp_rates')
        children_exoneration = self._rule_parameter('holiday_pay_pp_exoneration')
        children_reduction = self._rule_parameter('holiday_pay_pp_rate_reduction')

        employee = self.contract_id.employee_id

        if self.struct_id.code == "CP200DOUBLE":
            gross = categories['GROSS']
        elif self.struct_id.code == "CP200MONTHLY":
            gross = categories['DDPG']

        contract = self.contract_id
        monthly_revenue = contract._get_contract_wage()
        # Count ANT in yearly remuneration
        if contract.internet:
            monthly_revenue += 5.0
        if contract.mobile and not contract.internet:
            monthly_revenue += 4.0 + 5.0
        if contract.mobile and contract.internet:
            monthly_revenue += 4.0
        if contract.has_laptop:
            monthly_revenue += 7.0

        yearly_revenue = monthly_revenue * (1 - 0.1307) * 12.0

        if contract.transport_mode_car:
            if 'vehicle_id' in self:
                yearly_revenue += self.vehicle_id._get_car_atn(date=self.date_from) * 12.0
            else:
                yearly_revenue += contract.car_atn * 12.0

        # Exoneration
        children = employee.dependent_children
        if children > 0 and yearly_revenue <= children_exoneration.get(children, children_exoneration[12]):
            yearly_revenue -= children_exoneration.get(children, children_exoneration[12]) - yearly_revenue

        # Reduction
        if children > 0 and yearly_revenue <= children_reduction.get(children, children_reduction[5])[1]:
            withholding_tax_amount = gross * find_rates(yearly_revenue, rates) * (1 - children_reduction.get(children, children_reduction[5])[0] / 100.0)
        else:
            withholding_tax_amount = gross * find_rates(yearly_revenue, rates)
        return - withholding_tax_amount

    def _get_thirteen_month_withholding_taxes(self, localdict):
        self.ensure_one()
        # See: https://www.securex.eu/lex-go.nsf/vwReferencesByCategory_fr/52DA120D5DCDAE78C12584E000721081?OpenDocument
        def find_rates(x, rates):
            for low, high, rate in rates:
                if low <= x <= high:
                    return rate / 100.0

        categories = localdict['categories']
        rates = self._rule_parameter('exceptional_allowances_pp_rates')
        children_exoneration = self._rule_parameter('holiday_pay_pp_exoneration')
        children_reduction = self._rule_parameter('holiday_pay_pp_rate_reduction')

        employee = self.contract_id.employee_id

        gross = categories['GROSS']

        contract = self.contract_id
        monthly_revenue = contract._get_contract_wage()
        # Count ANT in yearly remuneration
        if contract.internet:
            monthly_revenue += 5.0
        if contract.mobile and not contract.internet:
            monthly_revenue += 4.0 + 5.0
        if contract.mobile and contract.internet:
            monthly_revenue += 4.0
        if contract.has_laptop:
            monthly_revenue += 7.0

        yearly_revenue = monthly_revenue * (1 - 0.1307) * 12.0

        if contract.transport_mode_car:
            if 'vehicle_id' in self:
                yearly_revenue += self.vehicle_id._get_car_atn(date=self.date_from) * 12.0
            else:
                yearly_revenue += contract.car_atn * 12.0

        # Exoneration
        children = employee.dependent_children
        if children > 0 and yearly_revenue <= children_exoneration.get(children, children_exoneration[12]):
            yearly_revenue -= children_exoneration.get(children, children_exoneration[12]) - yearly_revenue

        # Reduction
        if children > 0 and yearly_revenue <= children_reduction.get(children, children_reduction[5])[1]:
            withholding_tax_amount = gross * find_rates(yearly_revenue, rates) * (1 - children_reduction.get(children, children_reduction[5])[0] / 100.0)
        else:
            withholding_tax_amount = gross * find_rates(yearly_revenue, rates)
        return - withholding_tax_amount

    def _get_withholding_reduction(self, localdict):
        self.ensure_one()
        categories = localdict['categories']
        if categories['EmpBonus']:
            if self.date_from >= date(2024, 4, 1):
                bonus_volet_A = localdict['result_rules']['bonus_volet_A']['total']
                bonus_volet_B = localdict['result_rules']['bonus_volet_B']['total']
                reduction = bonus_volet_A * 0.3314 + bonus_volet_B * 0.5254
            else:
                reduction = categories['EmpBonus'] * 0.3314
            return min(abs(categories['PP']), reduction)
        return 0.0

    def _get_impulsion_plan_amount(self, localdict):
        self.ensure_one()
        start = self.employee_id.first_contract_date
        end = self.date_to
        number_of_months = (end.year - start.year) * 12 + (end.month - start.month)
        numerator = sum(wd.number_of_hours for wd in self.worked_days_line_ids if wd.amount > 0)
        denominator = 4 * self.contract_id.resource_calendar_id.hours_per_week
        coefficient = numerator / denominator
        if self.contract_id.l10n_be_impulsion_plan == '25yo':
            if 0 <= number_of_months <= 23:
                theorical_amount = 500.0
            elif 24 <= number_of_months <= 29:
                theorical_amount = 250.0
            elif 30 <= number_of_months <= 35:
                theorical_amount = 125.0
            else:
                theorical_amount = 0
            return min(theorical_amount, theorical_amount * coefficient)
        if self.contract_id.l10n_be_impulsion_plan == '12mo':
            if 0 <= number_of_months <= 11:
                theorical_amount = 500.0
            elif 12 <= number_of_months <= 17:
                theorical_amount = 250.0
            elif 18 <= number_of_months <= 23:
                theorical_amount = 125.0
            else:
                theorical_amount = 0
            return min(theorical_amount, theorical_amount * coefficient)
        return 0

    def _get_onss_restructuring(self, localdict):
        self.ensure_one()
        # Source: https://www.onem.be/fr/documentation/feuille-info/t115

        # 1. Grant condition
        # A worker who has been made redundant following a restructuring benefits from a reduction in his personal contributions under certain conditions:
        # - The engagement must take place during the validity period of the reduction card. The reduction card is valid for 6 months, calculated from date to date, following the termination of the employment contract.
        # - The gross monthly reference salary does not exceed
        # o 3.071.90: if the worker is under 30 years of age at the time of entry into service
        # o 4,504.93: if the worker is at least 30 years old at the time of entry into service
        # 2. Amount of reduction
        # Lump sum reduction of € 133.33 per month (full time - full month) in personal social security contributions.
        # If the worker does not work full time for a full month or if he works part time, this amount is reduced proportionally.

        # So the reduction is:
        # 1. Full-time worker: P = (J / D) x 133.33
        # - Full time with full one month benefits: € 133.33

        # Example the worker entered service on 02/01/2021 and worked the whole month
        # - Full time with incomplete services: P = (J / D) x 133.33
        # Example: the worker entered service on February 15 -> (10/20) x 133.33 = € 66.665
        # P = amount of reduction
        # J = the number of worker's days declared with a benefit code 1, 3, 4, 5 and 20 .;
        # D = the maximum number of days of benefits for the month concerned in the work scheme concerned.

        # 2. Part-time worker: P = (H / U) x 133.33
        # Example: the worker starts 02/01/2021 and works 19 hours a week.
        # (76/152) x 133.33 = € 66.665
        # Example: the worker starts 02/15/2021 and works 19 hours a week.
        # (38/155) x 133.33 = 33.335 €

        # P = amount of reduction
        # H = the number of working hours declared with a service code 1, 3, 4, 5 and 20;
        # U = the number of monthly hours corresponding to D.

        # 3. Duration of this reduction
        # The benefit applies to all periods of occupation that fall within the period that:
        # starts to run on the day you start your first occupation during the validity period of the restructuring reduction card;
        # and which ends on the last day of the second quarter following the start date of this first occupation.
        # 4. Formalities to be completed
        # The employer deducts the lump sum from the normal amount of personal contributions when paying the remuneration.
        # The ONEM communicates to the ONSS the data concerning the identification of the worker and the validity date of the card.

        # 5. Point of attention
        # If the worker also benefits from a reduction in his personal contributions for low wages, the cumulation between this reduction and that for restructuring cannot exceed the total amount of personal contributions due.

        # If this is the case, we must first reduce the restructuring reduction.

        # Example:
        # - personal contributions = 200 €
        # - restructuring reduction = € 133.33
        # - low salary reduction = 100 €

        # The total amount of reductions exceeds the contributions due. We must therefore first reduce the restructuring reduction and then the balance of the low wage reduction.
        if not self.worked_days_line_ids:
            return 0

        employee = self.contract_id.employee_id
        first_contract_date = employee.first_contract_date
        birthdate = employee.birthday
        age = relativedelta(first_contract_date, birthdate).years
        if age < 30:
            threshold = self._rule_parameter('onss_restructuring_before_30')
        else:
            threshold = self._rule_parameter('onss_restructuring_after_30')

        salary = self.paid_amount
        if salary > threshold:
            return 0

        amount = self._rule_parameter('onss_restructuring_amount')

        paid_hours = sum(self.worked_days_line_ids.filtered(lambda wd: wd.amount).mapped('number_of_hours'))
        total_hours = sum(self.worked_days_line_ids.mapped('number_of_hours'))
        ratio = paid_hours / total_hours if total_hours else 0

        start = first_contract_date
        end = self.date_to
        number_of_months = (end.year - start.year) * 12 + (end.month - start.month)
        if 0 <= number_of_months <= 6:
            return amount * ratio
        return 0

    def _get_representation_fees_threshold(self, localdict):
        return self._rule_parameter('cp200_representation_fees_threshold')

    def _get_representation_fees(self, localdict):
        self.ensure_one()
        categories = localdict['categories']
        worked_days = localdict['worked_days']
        contract = self.contract_id
        if not categories['BASIC']:
            result = 0
        else:
            calendar = contract.resource_calendar_id
            days_per_week = calendar._get_days_per_week()
            incapacity_attendances = calendar.attendance_ids.filtered(lambda a: a.work_entry_type_id.code == 'LEAVE281')
            if incapacity_attendances:
                incapacity_hours = sum((attendance.hour_to - attendance.hour_from) for attendance in incapacity_attendances)
                incapacity_hours = incapacity_hours / 2 if calendar.two_weeks_calendar else incapacity_hours
                incapacity_rate = (1 - incapacity_hours / calendar.hours_per_week) if calendar.hours_per_week else 0
                work_time_rate = contract.resource_calendar_id.work_time_rate * incapacity_rate
            else:
                work_time_rate = contract.resource_calendar_id.work_time_rate

            threshold = 0 if ('OUT' in worked_days and worked_days['OUT'].number_of_hours) else self._get_representation_fees_threshold(localdict)
            if days_per_week and self.env.context.get('salary_simulation_full_time'):
                result = contract.representation_fees
            elif days_per_week and contract.representation_fees > threshold:
                # Only part of the representation costs are pro-rated because certain costs are fully
                # covered for the company (teleworking costs, mobile phone, internet, etc., namely (for 2021):
                # - 144.31 € (Tax, since 2021 - coronavirus)
                # - 30 € (internet)
                # - 25 € (phone)
                # - 80 € (car management fees)
                # = Total € 279.31
                # Legally, they are not prorated according to the occupancy fraction.
                # In summary, those who select amounts of for example 150 € and 250 €, have nothing pro-rated
                # because the amounts are covered in an irreducible way.
                # For those who have selected the maximum of 399 €, there is therefore only the share of
                # +-120 € of representation expenses which is then subject to prorating.

                # Credit time, but with only half days (otherwise it's taken into account)
                if contract.time_credit and work_time_rate and work_time_rate < 100 and (days_per_week == 5 or not self.representation_fees_missing_days):
                    total_amount = threshold + (contract.representation_fees - threshold) * work_time_rate / 100
                # Contractual part time
                elif not contract.time_credit and work_time_rate < 100:
                    total_amount = threshold + (contract.representation_fees - threshold) * work_time_rate / 100
                else:
                    total_amount = contract.representation_fees

                if total_amount > threshold:
                    daily_amount = (total_amount - threshold) * 3 / 13 / days_per_week
                    result = max(0, total_amount - daily_amount * self.representation_fees_missing_days)
            elif days_per_week:
                result = contract.representation_fees
            else:
                result = 0
        return float_round(result, precision_digits=2)

    def _get_serious_representation_fees(self, localdict):
        self.ensure_one()
        return min(self._get_representation_fees(localdict), self._get_representation_fees_threshold(localdict))

    def _get_volatile_representation_fees(self, localdict):
        self.ensure_one()
        return max(self._get_representation_fees(localdict) - self._get_representation_fees_threshold(localdict), 0)

    def _get_holiday_pay_recovery(self, localdict, recovery_type):
        """
            See: https://www.socialsecurity.be/employer/instructions/dmfa/fr/latest/intermediates#intermediate_row_196b32c7-9d98-4233-805d-ca9bf123ff48

            When an employee changes employer, he receives the termination pay and a vacation certificate
            stating his vacation rights. When he subsequently takes vacation with his new employer, the latter
            must, when paying the simple vacation pay, take into account the termination pay that the former
            employer has already paid.

            From an exchange of letters with the SPF ETCS and the Inspectorate responsible for the control of
            social laws, it turned out that when calculating the simple vacation pay, the new employer must
            deduct the exit pay based on the number of vacation days taken. The rule in the ONSS instructions
            according to which the new employer must take into account the exit vacation pay only once when the
            employee takes his main vacation is abolished.

            When the salary of an employee with his new employer is higher than the salary he had with his
            previous employer, his new employer will have, each time he takes vacation days, to make a
            calculation to supplement the nest egg. exit from these days up to the amount of the simple vacation
            pay to which the worker is entitled.

            Concretely:

            2020 vacation certificate (full year):
            - simple allowance 1,917.50 EUR
                - this amounts to 1917.50 / 20 EUR = 95.875 EUR per day of vacation
                - holidays 2021, for example when taking 5 days in April 2021
            - monthly salary with the new employer: 3000.00 EUR / month
                - simple nest egg:
                     - remuneration code 12: 5/20 x 1917.50 = 479.38 EUR
                     - remuneration code 1: (5/22 x 3000.00) - 479.38 = 202.44 EUR
                - ordinary days for the month of April:
                    - remuneration code 1: 17/22 x 3000.00 = 2318.18 EUR
                    - The examples included in the ONSS instructions will be adapted in the next publication.
        """
        self.ensure_one()
        worked_days = localdict['worked_days']
        if 'LEAVE120' not in worked_days or not worked_days['LEAVE120'].amount:
            return 0
        employee = self.employee_id
        number_of_days = employee['l10n_be_holiday_pay_number_of_days_' + recovery_type]
        all_payslips_during_civil_year = self.env['hr.payslip'].search([
            ('employee_id', '=', employee.id),
            ('date_from', '>=', date(self.date_from.year, 1, 1)),
            ('date_to', '<=', date(self.date_from.year, 12, 31)),
            ('state', 'in', ['done', 'paid']),
        ])
        remaining_day = number_of_days - all_payslips_during_civil_year._get_worked_days_line_number_of_days('LEAVE120')
        if remaining_day <= 0:
            return 0
        if self.wage_type == 'hourly':
            employee_hourly_cost = self.contract_id.hourly_wage
        else:
            if self.date_from.year < 2024:
                employee_hourly_cost = self.contract_id.contract_wage / self.sum_worked_hours
            else:
                employee_hourly_cost = self.contract_id.contract_wage * 3 / 13 / self.contract_id.resource_calendar_id.hours_per_week
        remaining_day_amount = min(remaining_day, number_of_days) * employee_hourly_cost * 7.6
        days_to_recover = employee['l10n_be_holiday_pay_to_recover_' + recovery_type]
        max_amount_to_recover = min(days_to_recover, employee_hourly_cost * number_of_days * 7.6)
        leave120_amount = self._get_worked_days_line_amount('LEAVE120')
        holiday_amount = min(leave120_amount, employee_hourly_cost * self._get_worked_days_line_number_of_hours('LEAVE120'))
        remaining_amount = max(0, max_amount_to_recover - employee['l10n_be_holiday_pay_recovered_' + recovery_type])
        return - min(remaining_amount, remaining_day_amount, holiday_amount)

    def _get_holiday_pay_recovery_n(self, localdict):
        return self._get_holiday_pay_recovery(localdict, 'n')

    def _get_holiday_pay_recovery_n1(self, localdict):
        return self._get_holiday_pay_recovery(localdict, 'n1')

    def _get_termination_n_basic_double(self, localdict):
        self.ensure_one()
        inputs = localdict['inputs']
        result_qty = 1
        result_rate = 6.8
        result = inputs['GROSS_REF'].amount if 'GROSS_REF' in inputs else 0
        date_from = self.date_from
        if self.struct_id.code == "CP200HOLN1":
            existing_double_pay = self.env['hr.payslip'].search([
                ('employee_id', '=', self.employee_id.id),
                ('state', 'in', ['done', 'paid']),
                ('struct_id', '=', self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id),
                ('date_from', '>=', date(date_from.year, 1, 1)),
                ('date_to', '<=', date(date_from.year, 12, 31)),
            ])
            if existing_double_pay:
                result = 0
        return (result_qty, result_rate, result)
