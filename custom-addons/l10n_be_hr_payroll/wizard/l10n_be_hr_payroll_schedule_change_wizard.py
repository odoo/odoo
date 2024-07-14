# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_round

from datetime import timedelta
from markupsafe import Markup

class L10nBeHrPayrollScheduleChange(models.TransientModel):
    _name = 'l10n_be.hr.payroll.schedule.change.wizard'
    _description = 'Change contract working schedule'

    contract_id = fields.Many2one(
        'hr.contract', string='Contract', readonly=True,
        default=lambda self: self.env.context.get('active_id'),
    )
    company_id = fields.Many2one(related='contract_id.company_id', readonly=True)
    employee_id = fields.Many2one(related='contract_id.employee_id', readonly=True)
    structure_type_id = fields.Many2one(related='contract_id.structure_type_id', readonly=True)
    date_start = fields.Date('Start Date', help='Start date of the new contract.', required=True)
    date_end = fields.Date('End Date', help='End date of the new contract.')
    work_time_rate = fields.Float(related='resource_calendar_id.work_time_rate', readonly=True)
    full_wage = fields.Monetary('Full Time Equivalent Wage', compute='_compute_wages', store=True, readonly=True)
    current_wage = fields.Monetary('Wage', compute='_compute_wages', store=True, readonly=True)
    wage = fields.Monetary(
        compute='_compute_wages', store=True, readonly=False,
        string='New Wage', required=True,
        help="Employee's monthly gross wage for the new contract.")
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)
    previous_contract_creation = fields.Boolean('Post Change Contract Creation',
        help='If checked, the wizard will create another contract after the new working schedule contract, with current working schedule',
        default=False)

    full_resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Full Working Schedule',
        related='structure_type_id.default_resource_calendar_id')
    current_resource_calendar_id = fields.Many2one(
        'resource.calendar',
        'Current Working Schedule',
        related='contract_id.resource_calendar_id')
    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'New Working Schedule', required=True,
        default=lambda self: self.env.company.resource_calendar_id.id,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    part_time = fields.Boolean()
    presence_work_entry_type_id = fields.Many2one(
        'hr.work.entry.type',
        related='structure_type_id.default_work_entry_type_id')
    absence_work_entry_type_id = fields.Many2one(
        'hr.work.entry.type', string='Absence Work Entry Type',
        help='The work entry type used when generating work entries to fit full time working schedule.')

    leave_type_id = fields.Many2one(
        'hr.leave.type', string='Time Off Type', required=True,
        domain=[('requires_allocation', '=', 'yes')],
        default=lambda self: self.env['hr.leave.type'].search([], limit=1))
    full_time_off_allocation = fields.Float(compute='_compute_full_time_off_allocation', readonly=True)
    time_off_allocation = fields.Float(
        compute='_compute_time_off_allocation', store=True,
        help="The computed amount is the sum of the new right to time off and the number of time off already taken by the employee. Example: Moving from a full time to a 4/5 part time with 6 days already taken will result into an amount of 80%% of 14 days + 6 days (rounded down) = 17 days.")
    leave_allocation_id = fields.Many2one('hr.leave.allocation', compute='_compute_leave_allocation_id')
    found_leave_allocation = fields.Boolean(compute='_compute_leave_allocation_id')
    initial_time_off_allocation = fields.Float(compute='_compute_leave_allocation_id')

    requires_new_contract = fields.Boolean(compute='_compute_requires_new_contract')

    @api.depends('work_time_rate', 'current_resource_calendar_id')
    def _compute_wages(self):
        for wizard in self:
            #Compute full wage first since wage depends on it
            wizard.current_wage = wizard.contract_id._get_contract_wage()
            work_time_rate = wizard.current_resource_calendar_id.work_time_rate
            wizard.full_wage = wizard.current_wage / ((work_time_rate / 100) if work_time_rate else 1)
            wizard.wage = wizard.full_wage * float(wizard.work_time_rate) / 100

    @api.depends('leave_type_id', 'full_resource_calendar_id')
    def _compute_full_time_off_allocation(self):
        # NOTE: Hard coded to 20, this might cause issues later but we can't thing of any case where
        #  it is not 20 but kept as a compute for it to be easier to adapt if necessary
        self.write({
            'full_time_off_allocation': 20,
        })

    @api.model
    def _compute_new_allocation(self, leave_allocation, current_calendar, new_calendar, date_start):
        if current_calendar.hours_per_week == 0 or not leave_allocation:
            return 0

        # Simulate the start of year allocation to have an accurate value
        paid_leave_wizard = self.env['hr.payroll.alloc.paid.leave']\
            .with_company(leave_allocation.employee_company_id).with_context(forced_calendar=new_calendar).new({
                'year': str(date_start.year - 1),
                'holiday_status_id': leave_allocation.holiday_status_id.id,
                'employee_ids': leave_allocation.employee_id,
            })
        if paid_leave_wizard.alloc_employee_ids:
            new_allocation = max(0, paid_leave_wizard.alloc_employee_ids[0].paid_time_off_to_allocate - leave_allocation.leaves_taken)
        else:
            new_allocation = 0

        # There is a maximum that we should never pass, in theory we should never pass that limit
        # since we round down, but since the payroll officer will not be able to modify this values
        # it is good to have that limit
        max_allocation = ((len(new_calendar.attendance_ids) * 4) / 2 if not new_calendar.two_weeks_calendar
            else (len(new_calendar.attendance_ids) * 2 / 2)) - leave_allocation.leaves_taken

        # An allocation's number of days may never be below the number of leaves taken
        return max(min(new_allocation, max_allocation) + leave_allocation.leaves_taken, leave_allocation.leaves_taken)

    @api.depends('leave_allocation_id', 'resource_calendar_id', 'date_start')
    def _compute_time_off_allocation(self):
        for wizard in self:
            date_start = wizard.date_start or fields.Date().today()
            wizard.time_off_allocation = self._compute_new_allocation(
                wizard.leave_allocation_id, wizard.current_resource_calendar_id,
                wizard.resource_calendar_id, date_start,
            )

    @api.depends('leave_type_id')
    def _compute_leave_allocation_id(self):
        no_leave_wizards = self.env['l10n_be.hr.payroll.schedule.change.wizard']
        for wizard in self:
            if not wizard.leave_type_id:
                no_leave_wizards |= wizard
                continue
            leave_allocation = self.env['hr.leave.allocation'].search([
                ('holiday_status_id', '=', wizard.leave_type_id.id),
                ('employee_id', '=', wizard.contract_id.employee_id.id),
                ('state', 'in', ['validate'])], limit=1)
            if not leave_allocation or len(leave_allocation) > 1:
                no_leave_wizards |= wizard
                continue
            wizard.write({
                'leave_allocation_id': leave_allocation.id,
                'found_leave_allocation': True,
                'initial_time_off_allocation': leave_allocation.number_of_days,
            })
        no_leave_wizards.write({
            'leave_allocation_id': False,
            'found_leave_allocation': False,
            'initial_time_off_allocation': False,
        })

    @api.depends('contract_id', 'date_start')
    def _compute_requires_new_contract(self):
        # NOTE: this might need more checks
        requires_new_contract = self.filtered(lambda w: (
            not w.date_start or
            not w.contract_id or
            w.date_start <= w.contract_id.date_start
        ))
        requires_new_contract.write({'requires_new_contract': True})
        (self - requires_new_contract).write({'requires_new_contract': False})

    @api.onchange('work_time_rate')
    def _onchange_work_time_rate(self):
        #This case will be checked again when validating, onchange is ok
        self.filtered(lambda w: w.part_time and w.work_time_rate >= 100).write({
            'part_time': False,
        })

    def _update_allocation_or_schedule(self, date, contract, current, new, max_days):
        self.ensure_one()
        if not self.leave_allocation_id:
            return
        if date > fields.Date.today() or self.env.context.get('force_schedule', False):
            # Schedule for cron
            self.env['l10n_be.schedule.change.allocation'].create({
                'effective_date': date,
                'contract_id': contract.id,
                'current_resource_calendar_id': current.id,
                'new_resource_calendar_id': new.id,
                'leave_allocation_id': self.leave_allocation_id.id,
                'maximum_days': max_days
            })
        else:
            # NOTE: for now we don't check the period but since creating a part time contract for a
            #  previous period is pretty weird something like this might be needed:
            # not self.date_end or self.date_end >= fields.Date.today()
            # Update directly, use initial time off allocation if this is the continuation contract
            new_total = self.time_off_allocation if new != self.contract_id.resource_calendar_id else self.initial_time_off_allocation
            self.leave_allocation_id.write({
                'number_of_days': new_total,
            })
            self.leave_allocation_id._message_log(body=Markup(_('New working schedule on %(contract_name)s.<br/>'
            'New total: %(days)s')) % {'contract_name': contract.name, 'days': new_total})

    def action_validate(self):
        self.ensure_one()
        if self.contract_id.resource_calendar_id == self.resource_calendar_id:
            raise ValidationError(_('Working schedule would stay unchanged by this action. Please select another working schedule.'))
        if self.date_end and self.date_start > self.date_end:
            raise ValidationError(_('Start date must be earlier than end date.'))
        if self.date_start < self.contract_id.date_start:
            raise ValidationError(_('Start date must be later than the current contract\'s start date.'))
        if self.contract_id.date_end and self.date_end and self.contract_id.date_end < self.date_end:
            raise ValidationError(_('Current contract is finished before the end of the new contract.'))

        if self.part_time and self.work_time_rate >= 100:
            self.part_time = False

        if self.part_time:
            name = _('%s - Part Time %s', self.employee_id.name, self.resource_calendar_id.name)
        else:
            name = f'{self.employee_id.name} - {self.resource_calendar_id.name}'

        new_contracts = self.contract_id.copy({
            'name': name,
            'date_start': self.date_start,
            'date_end': self.date_end,
            self.contract_id._get_contract_wage_field(): self.wage,
            'resource_calendar_id': self.resource_calendar_id.id,
            'standard_calendar_id': self.full_resource_calendar_id.id,
            'time_credit': self.part_time,
            'work_time_rate': self.work_time_rate / 100 if self.part_time else False,
            'state': 'draft',
            'time_credit_type_id': self.absence_work_entry_type_id.id if self.part_time else None
        })
        # Since _get_contract_wage_field is not always 'wage' we also want to change the original wage
        if new_contracts._get_contract_wage_field() != 'wage':
            new_contracts.wage = self.wage

        # Process allocation changes
        if self.leave_allocation_id:
            original_allocated_days = self.leave_allocation_id.number_of_days - self.leave_allocation_id.leaves_taken
            self._update_allocation_or_schedule(
                self.date_start,
                new_contracts[0],
                self.current_resource_calendar_id,
                self.resource_calendar_id,
                self.full_time_off_allocation,
            )

        if self.date_end and (
            not self.contract_id.date_end
            or (self.date_end + timedelta(days=1)) < self.contract_id.date_end):

            # Create a contract for the rest of the original contrat's time period if it exists
            if self.previous_contract_creation:
                post_contract = self.contract_id.copy({
                    'date_start': (self.date_end + timedelta(days=1)),
                    # resource_calendar_id is copy=False
                    'resource_calendar_id': self.contract_id.resource_calendar_id.id,
                    'state': 'draft',
                })
                new_contracts |= post_contract
                # We also need to update the allocation when this contract starts,
                #  basically revert back changes
                if self.leave_allocation_id:
                    self._update_allocation_or_schedule(
                        post_contract.date_start,
                        post_contract,
                        self.resource_calendar_id,
                        self.current_resource_calendar_id,
                        original_allocated_days,
                    )

        # Set a closing date on the current contract
        contract_date_end = self.date_start
        if self.date_start != self.contract_id.date_start:
            contract_date_end -= timedelta(days=1)
        self.with_context(close_contract=False).contract_id.date_end = contract_date_end

        # When changing the schedule from the contract history we can just reload the view instead of going on to a separate view
        if self.env.context.get('from_history', False):
            return True
        else:
            return {
                'name': _('Credit time contract'),
                'domain': [('id', 'in', (new_contracts | self.contract_id).ids)],
                'res_model': 'hr.contract',
                'view_id': False,
                'view_mode': 'tree,form',
                'type': 'ir.actions.act_window',
            }
