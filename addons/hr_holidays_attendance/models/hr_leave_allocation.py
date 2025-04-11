# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression

from odoo.tools.date_utils import get_timedelta


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    def default_get(self, fields):
        res = super().default_get(fields)
        if 'holiday_status_id' in fields and self.env.context.get('deduct_extra_hours'):
            domain = [('overtime_deductible', '=', True), ('requires_allocation', '=', 'yes')]
            if self.env.context.get('deduct_extra_hours_employee_request', False):
                # Prevent loading manager allocated time off type in self request contexts
                domain = expression.AND([domain, [('employee_requests', '=', 'yes')]])
            leave_type = self.env['hr.leave.type'].search(domain, limit=1)
            res['holiday_status_id'] = leave_type.id
        return res

    overtime_deductible = fields.Boolean(compute='_compute_overtime_deductible')
    overtime_id = fields.Many2one('hr.attendance.overtime', string='Extra Hours', groups='hr_holidays.group_hr_holidays_user')
    employee_overtime = fields.Float(related='employee_id.total_overtime', groups='base.group_user')

    @api.depends('holiday_status_id')
    def _compute_overtime_deductible(self):
        for allocation in self:
            allocation.overtime_deductible = allocation.holiday_status_id.overtime_deductible

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for allocation in res:
            if allocation.overtime_deductible:
                duration = allocation.number_of_hours_display
                if duration > allocation.employee_id.sudo().total_overtime:
                    raise ValidationError(_('The employee does not have enough overtime hours to request this leave.'))
                if not allocation.overtime_id:
                    allocation.sudo().overtime_id = self.env['hr.attendance.overtime'].sudo().create({
                        'employee_id': allocation.employee_id.id,
                        'date': allocation.date_from,
                        'adjustment': True,
                        'duration': -1 * duration,
                    })
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'number_of_days' not in vals:
            return res
        if not self.env.user.has_group("hr_holidays.group_hr_holidays_user") and any(allocation.state not in ('draft', 'confirm') for allocation in self):
            raise ValidationError(_('Only an Officer or Administrator is allowed to edit the allocation duration in this status.'))
        for allocation in self.sudo().filtered('overtime_id'):
            employee = allocation.employee_id
            duration = allocation.number_of_hours_display
            overtime_duration = allocation.overtime_id.sudo().duration
            if overtime_duration != -1 * duration:
                if duration > employee.total_overtime - overtime_duration:
                    raise ValidationError(_('The employee does not have enough extra hours to extend this allocation.'))
                allocation.overtime_id.sudo().duration = -1 * duration
        return res

    def action_refuse(self):
        res = super().action_refuse()
        self.overtime_id.sudo().unlink()
        return res

    def _get_accrual_plan_level_work_entry_prorata(self, level, start_period, start_date, end_period, end_date):
        self.ensure_one()
        if level.frequency != 'worked_hours':
            return super()._get_accrual_plan_level_work_entry_prorata(level, start_period, start_date, end_period, end_date)
        datetime_min_time = datetime.min.time()
        start_dt = datetime.combine(start_date, datetime_min_time)
        end_dt = datetime.combine(end_date, datetime_min_time)
        attendances = self.env['hr.attendance'].sudo().search([
            ('employee_id', '=', self.employee_id.id),
            ('check_in', '>=', start_dt),
            ('check_out', '<=', end_dt),
        ])
        work_entry_prorata = sum(attendances.mapped('worked_hours'))
        return work_entry_prorata

    def _process_accrual_plan_level(self, level, start_period, start_date, end_period, end_date):
        """
        Returns the added days for that level
        """
        if level.frequency == 'worked_hours':
            level.frequency = "hourly"
        return super()._process_accrual_plan_level(level, start_period, start_date, end_period, end_date)

    def _process_accrual_plans(self, date_to=False, force_period=False, log=True):
        """
        This method is part of the cron's process.
        The goal of this method is to retroactively apply accrual plan levels and progress from nextcall to date_to or today.
        If force_period is set, the accrual will run until date_to in a prorated way (used for end of year accrual actions).
        """

        date_to = date_to or fields.Date.today()
        already_accrued = {allocation.id: allocation.already_accrued or (allocation.number_of_days != 0 and allocation.accrual_plan_id.accrued_gain_time == 'start') for allocation in self}
        first_allocation = _("""This allocation have already ran once, any modification won't be effective to the days allocated to the employee. If you need to change the configuration of the allocation, delete and create a new one.""")
        for allocation in self:
            level_ids = allocation.accrual_plan_id.level_ids.sorted('sequence')
            if not level_ids:
                continue
            # "cache" leaves taken, as it gets recomputed every time allocation.number_of_days is assigned to. Without this,
            # every loop will take 1+ second. It can be removed if computes don't chain in a way to always reassign accrual plan
            # even if the value doesn't change. This is the best performance atm.
            first_level = level_ids[0]
            first_level_start_date = allocation.date_from + get_timedelta(first_level.start_count, first_level.start_type)
            if allocation.holiday_status_id.request_unit in ["day", "half_day"]:
                leaves_taken = allocation.leaves_taken
            else:
                leaves_taken = allocation.leaves_taken / allocation.employee_id._get_hours_per_day(allocation.date_from)
            allocation.already_accrued = already_accrued[allocation.id]
            # first time the plan is run, initialize nextcall and take carryover / level transition into account
            if not allocation.nextcall:
                # Accrual plan is not configured properly or has not started
                if date_to < first_level_start_date:
                    continue
                allocation.lastcall = max(allocation.lastcall, first_level_start_date)
                allocation.actual_lastcall = allocation.lastcall
                allocation.nextcall = first_level._get_next_date(allocation.lastcall)
                # adjust nextcall for carryover
                carryover_date = allocation._get_carryover_date(allocation.nextcall)
                allocation.nextcall = min(carryover_date, allocation.nextcall)
                # adjust nextcall for level_transition
                if len(level_ids) > 1:
                    second_level_start_date = allocation.date_from + get_timedelta(level_ids[1].start_count, level_ids[1].start_type)
                    allocation.nextcall = min(second_level_start_date, allocation.nextcall)
                if log:
                    allocation._message_log(body=first_allocation)
            (current_level, current_level_idx) = (False, 0)
            current_level_maximum_leave = 0.0
            # all subsequent runs, at every loop:
            # get current level and normal period boundaries, then set nextcall, adjusted for level transition and carryover
            # add days, trimmed if there is a maximum_leave
            while allocation.nextcall <= date_to:
                (current_level, current_level_idx) = allocation._get_current_accrual_plan_level_id(allocation.nextcall)
                if not current_level:
                    break
                if current_level.cap_accrued_time:
                    if current_level.added_value_type == "day":
                        current_level_maximum_leave = current_level.maximum_leave
                    else:
                        current_level_maximum_leave = current_level.maximum_leave / allocation.employee_id._get_hours_per_day(allocation.date_from)
                nextcall = current_level._get_next_date(allocation.nextcall)
                # Since _get_previous_date returns the given date if it corresponds to a call date
                # this will always return lastcall except possibly on the first call
                # this is used to prorate the first number of days given to the employee
                period_start = current_level._get_previous_date(allocation.lastcall)
                period_end = current_level._get_next_date(allocation.lastcall)
                # There are 3 cases where nextcall could be closer than the normal period:
                # 1. Passing from one level to another, if mode is set to 'immediately'
                current_level_last_date = False
                if current_level_idx < (len(level_ids) - 1) and allocation.accrual_plan_id.transition_mode == 'immediately':
                    next_level = level_ids[current_level_idx + 1]
                    current_level_last_date = allocation.date_from + get_timedelta(next_level.start_count, next_level.start_type)
                    if allocation.nextcall != current_level_last_date:
                        nextcall = min(nextcall, current_level_last_date)
                # 2. On carry-over date
                carryover_date = allocation._get_carryover_date(allocation.nextcall)
                if allocation.nextcall < carryover_date < nextcall:
                    nextcall = min(nextcall, carryover_date)

                if current_level.accrual_validity:
                    # 3. On carried over days expiration date
                    expiration_date = allocation.carried_over_days_expiration_date
                    # - not expiration_date -> expiration_date needs to be initialized.
                    # - allocation.nextcall > expiration_date -> the expiration date has passed and the new one should be computed.
                    # - allocation.expiring_carryover_days == 0 -> If the carryover date of the accrual plan was changed or if a level
                    #   transition occurred, then the expiration date needs to be updated. However, if allocation.expiring_carryover_days != 0,
                    #   then this means that some days will expire on expiration_date and that expiration date should be respected and
                    #   Expiration date will be updated correctly when allocation.nextcall is greater than expiration_date.
                    if not expiration_date or allocation.nextcall > expiration_date or allocation.expiring_carryover_days == 0:
                        expiration_date = carryover_date + relativedelta(**{current_level.accrual_validity_type + 's': current_level.accrual_validity_count})
                        allocation.carried_over_days_expiration_date = expiration_date
                    if allocation.nextcall < expiration_date < nextcall:
                        nextcall = expiration_date
                    if allocation.nextcall == expiration_date:
                        # Given that allocation.number_of_days = employee time off balance + leaves_taken. So,
                        # the leaves_taken are included in allocation.number_of_days.
                        # Also, allocation.expiring_carryover_days includes the leaves_taken before the carryover date
                        # and allocation.leaves_taken includes all the leaves_taken before the carryover date + all the leaves_taken
                        # between the carryover date and the expiration_date. So, the number of expiring days will be
                        # allocation.expiring_carryover_days - allocation.leaves_taken or 0 if all the expiring days were used
                        # to take time off.
                        # This ensures that only the days that weren't used to take time off will expire.
                        expiring_days = max(0, allocation.expiring_carryover_days - allocation.leaves_taken)
                        allocation.number_of_days = max(0, allocation.number_of_days - expiring_days)
                        allocation.expiring_carryover_days = 0

                # if it's the carry-over date, adjust days using current level's carry-over policy
                if allocation.nextcall == carryover_date:
                    allocation.last_executed_carryover_date = carryover_date
                    if current_level.action_with_unused_accruals == 'lost' or current_level.carryover_options == 'limited':
                        allocated_days_left = allocation.number_of_days - leaves_taken
                        allocation_max_days = 0 # default if unused_accrual are lost
                        if current_level.carryover_options == 'limited':
                            if current_level.added_value_type == 'day':
                                postpone_max_days = current_level.postpone_max_days
                            else:
                                postpone_max_days = current_level.postpone_max_days / allocation.employee_id._get_hours_per_day(allocation.date_from)
                            allocation_max_days = min(postpone_max_days, allocated_days_left)
                        allocation.number_of_days = min(allocation.number_of_days, allocation_max_days) + leaves_taken
                    allocation.expiring_carryover_days = allocation.number_of_days

                # Only accrue on the end of the accrual period or on level transition date
                is_accrual_date = allocation.nextcall == period_end or allocation.nextcall == current_level_last_date
                if not allocation.already_accrued and is_accrual_date:
                    allocation._add_days_to_allocation(current_level, current_level_maximum_leave, leaves_taken, period_start, period_end)

                if allocation.nextcall == carryover_date:
                    allocation.yearly_accrued_amount = 0

                # 1. When accrued_gain_time == 'start', all the days are accrued on the start of the accrual period. For example, if the accrual period
                #    is from 01/01/2023 to 01/01/2024, then the days will be accrued on 01/01/2023. Given that the carryover date will be >= the start of the accrual period
                #    (01/01/2023 in the example) the carryover policy should apply to any day accrued during the period from 01/01/2023 to 01/01/2024.
                # 2.However, if a level transistion occurred, the carryover policy should apply to the days that were accrued during the carryover level only.
                #   Any days accrued after the carryover level should be excluded.
                #   So, if carryover date was 01/06/2023, it should be applied to any day accrued between 01/01/2023 and 01/01/2024. If a level transition
                #   occurred on 01/09/2023 for example, then the carryover should be applied to any day accrued between 01/01/2023 and 01/09/2023.
                # 3. The following if block will handle the carryover for days accrued after carryover_date until carryover_period_end. Carryover period end is
                #    adjusted if a level transition occurred. The carryover for days accrued before carryover_date is handled above.
                if allocation.accrual_plan_id.accrued_gain_time == 'start' and allocation.last_executed_carryover_date:
                    last_carryover_date = allocation.last_executed_carryover_date
                    carryover_level, carryover_level_idx = allocation._get_current_accrual_plan_level_id(last_carryover_date)
                    carryover_period_end = carryover_level._get_next_date(last_carryover_date)
                    # Adjust carryover_period_end based on level_transition.
                    if carryover_level_idx < (len(level_ids) - 1) and allocation.accrual_plan_id.transition_mode == 'immediately':
                        next_level = level_ids[carryover_level_idx + 1]
                        carryover_level_last_date = allocation.date_from + get_timedelta(next_level.start_count, next_level.start_type)
                        carryover_period_end = min(carryover_period_end, carryover_level_last_date)
                    # Handle the special case for hourly/daily accruals. Carryover_period_end should be equal to last_carryover_date
                    # because the carryover period is just 1 day.
                    if carryover_level.frequency == 'hourly' or carryover_level.frequency == 'daily' or carryover_level.frequency == 'worked_hours':
                        carryover_period_end = last_carryover_date
                    # Carryover policy should be only applied to the days accrued on period_end.
                    # Days accrued on level transition date aren't subject to the carryover policy.
                    # That is why (allocation.nextcall == period_end) is used instead of (is_accrual_date)
                    accrued = not allocation.already_accrued and allocation.nextcall == period_end
                    # If the days were accrued on the carryover period, then apply the carryover policy
                    if accrued and last_carryover_date <= allocation.nextcall <= carryover_period_end:
                        if carryover_level.action_with_unused_accruals == 'lost' or carryover_level.carryover_options == 'limited':
                            allocation.last_executed_carryover_date = carryover_date
                            allocated_days_left = allocation.number_of_days - leaves_taken
                            postpone_max_days = current_level.postpone_max_days if current_level.added_value_type == 'day' \
                                else current_level.postpone_max_days / allocation.employee_id._get_hours_per_day(allocation.date_from)
                            allocated_days_left = allocation.number_of_days - leaves_taken
                            allocation_max_days = 0 # default if unused_accrual are lost
                            if current_level.carryover_options == 'limited':
                                postpone_max_days = current_level.postpone_max_days
                                allocation_max_days = min(postpone_max_days, allocated_days_left)
                            allocation.number_of_days = min(allocation.number_of_days, allocation_max_days) + leaves_taken

                if is_accrual_date:
                    allocation.lastcall = allocation.nextcall
                allocation.actual_lastcall = allocation.nextcall
                allocation.nextcall = nextcall
                allocation.already_accrued = False
                if force_period and allocation.nextcall > date_to:
                    allocation.nextcall = date_to
                    force_period = False

            # if plan.accrued_gain_time == 'start', process next period and set flag 'already_accrued', this will skip adding days
            # once, preventing double allocation.
            if allocation.accrual_plan_id.accrued_gain_time == 'start':
                # check that we are at the start of a period, not on a carry-over or level transition date
                level_start = {level._get_level_transition_date(allocation.date_from): level for level in allocation.accrual_plan_id.level_ids}
                current_level = level_start.get(allocation.actual_lastcall) or current_level or allocation.accrual_plan_id.level_ids[0]
                period_start = current_level._get_previous_date(allocation.actual_lastcall)
                if current_level.cap_accrued_time:
                    if current_level.added_value_type == "day":
                        current_level_maximum_leave = current_level.maximum_leave
                    else:
                        current_level_maximum_leave = current_level.maximum_leave / allocation.employee_id._get_hours_per_day(allocation.date_from)
                if allocation.actual_lastcall in {period_start, allocation.date_from} | set(level_start.keys()):
                    allocation._add_days_to_allocation(current_level, current_level_maximum_leave, leaves_taken, period_start, allocation.nextcall)
                    allocation.already_accrued = True
