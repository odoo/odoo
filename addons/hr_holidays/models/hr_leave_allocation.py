# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)

import logging

from datetime import datetime, time
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.addons.resource.models.resource import HOURS_PER_DAY
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.translate import _
from odoo.tools.float_utils import float_round
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class HolidaysAllocation(models.Model):
    """ Allocation Requests Access specifications: similar to leave requests """
    _name = "hr.leave.allocation"
    _description = "Time Off Allocation"
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'

    def _default_holiday_status_id(self):
        if self.user_has_groups('hr_holidays.group_hr_holidays_user'):
            domain = [('valid', '=', True), ('allocation_type', '!=', 'no')]
        else:
            domain = [('valid', '=', True), ('allocation_type', '=', 'fixed_allocation')]
        return self.env['hr.leave.type'].search(domain, limit=1)

    def _holiday_status_id_domain(self):
        if self.user_has_groups('hr_holidays.group_hr_holidays_manager'):
            return [('valid', '=', True), ('allocation_type', '!=', 'no')]
        return [('valid', '=', True), ('allocation_type', '=', 'fixed_allocation')]

    name = fields.Char('Description', compute='_compute_description', inverse='_inverse_description', search='_search_description', compute_sudo=False)
    private_name = fields.Char('Allocation Description', groups='hr_holidays.group_hr_holidays_user')
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('cancel', 'Cancelled'),
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved')
        ], string='Status', readonly=True, tracking=True, copy=False, default='confirm',
        help="The status is set to 'To Submit', when an allocation request is created." +
        "\nThe status is 'To Approve', when an allocation request is confirmed by user." +
        "\nThe status is 'Refused', when an allocation request is refused by manager." +
        "\nThe status is 'Approved', when an allocation request is approved by manager.")
    date_from = fields.Datetime(
        'Start Date', readonly=True, index=True, copy=False, default=fields.Date.context_today,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, tracking=True)
    date_to = fields.Datetime(
        'End Date', compute='_compute_from_holiday_status_id', store=True, readonly=False, copy=False, tracking=True,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)], 'validate': [('readonly', True)]})
    holiday_status_id = fields.Many2one(
        "hr.leave.type", compute='_compute_from_employee_id', store=True, string="Time Off Type", required=True, readonly=False,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)], 'validate': [('readonly', True)]},
        domain=_holiday_status_id_domain, default=_default_holiday_status_id)
    employee_id = fields.Many2one(
        'hr.employee', compute='_compute_from_holiday_type', store=True, string='Employee', index=True, readonly=False, ondelete="restrict", tracking=True,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)], 'validate': [('readonly', True)]})
    manager_id = fields.Many2one('hr.employee', compute='_compute_from_employee_id', store=True, string='Manager')
    notes = fields.Text('Reasons', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    # duration
    number_of_days = fields.Float(
        'Duration', compute='_compute_from_holiday_status_id', store=True, readonly=False, tracking=True,
        help='Duration in days. Reference field to use when necessary.')
    extra_days = fields.Float(
        'Initial Allocated Days', store=True, readonly=False, default=0,
        help='Number of days allocated in addition to the ones you will get via the accrual system.')
    number_of_days_display = fields.Float(
        'Duration (days)', compute='_compute_number_of_days_display',
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        help="If Accrual Allocation: Number of days allocated in addition to the ones you will get via the accrual' system.")
    number_of_hours_display = fields.Float(
        'Duration (hours)', compute='_compute_number_of_hours_display',
        help="If Accrual Allocation: Number of hours allocated in addition to the ones you will get via the accrual' system.")
    duration_display = fields.Char('Allocated (Days/Hours)', compute='_compute_duration_display',
        help="Field allowing to see the allocation duration in days or hours depending on the type_request_unit")
    first_approver_id = fields.Many2one(
        'hr.employee', string='First Approval', readonly=True, copy=False,
        help='This area is automatically filled by the user who validates the allocation')
    second_approver_id = fields.Many2one(
        'hr.employee', string='Second Approval', readonly=True, copy=False,
        help='This area is automatically filled by the user who validates the allocation with second level (If allocation type need second validation)')
    validation_type = fields.Selection(string='Validation Type', related='holiday_status_id.allocation_validation_type', readonly=True)
    can_reset = fields.Boolean('Can reset', compute='_compute_can_reset')
    can_approve = fields.Boolean('Can Approve', compute='_compute_can_approve')
    type_request_unit = fields.Selection(related='holiday_status_id.request_unit', readonly=True)
    # mode
    holiday_type = fields.Selection([
        ('employee', 'By Employee'),
        ('company', 'By Company'),
        ('department', 'By Department'),
        ('category', 'By Employee Tag')],
        string='Allocation Mode', readonly=True, required=True, default='employee',
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        help="Allow to create requests in batchs:\n- By Employee: for a specific employee"
             "\n- By Company: all employees of the specified company"
             "\n- By Department: all employees of the specified department"
             "\n- By Employee Tag: all employees of the specific employee group category")
    mode_company_id = fields.Many2one(
        'res.company', compute='_compute_from_holiday_type', store=True, string='Company Mode', readonly=False,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)], 'validate': [('readonly', True)]})
    department_id = fields.Many2one(
        'hr.department', compute='_compute_department_id', store=True, string='Department',
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    category_id = fields.Many2one(
        'hr.employee.category', compute='_compute_from_holiday_type', store=True, string='Employee Tag', readonly=False,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)], 'validate': [('readonly', True)]})
    # accrual configuration
    accrual_plan_id = fields.Many2one('hr.leave.accrual.plan', string='Accrual Plan')
    linked_request_ids = fields.One2many('hr.leave.allocation.item', 'allocation_id', compute='_compute_allocation_item')
    allocation_item_count = fields.Integer(compute='_compute_allocation_item_count')
    allocation_type = fields.Selection(
        [
            ('regular', 'Regular Allocation'),
            ('accrual', 'Accrual Allocation')
        ], string="Allocation Type", default="regular", required=True, readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    target = fields.Char(compute='_compute_from_holiday_type', compute_sudo=True)
    nextcall = fields.Date("Date of the next accrual allocation", default=False, readonly=True)
    max_leaves = fields.Float(compute='_compute_leaves')
    leaves_taken = fields.Float(compute='_compute_leaves')
    aggretated_duration = fields.Char(compute='_compute_agregated_duration',
                                       help="Display the allocation duration. Straightforward for regular allocations. "
                                            "Accrual: The extra days or the exact amount of days when accrual allocation of single employees ")

    _sql_constraints = [
        ('type_value',
         "CHECK( (holiday_type='employee' AND employee_id IS NOT NULL) or "
         "(holiday_type='category' AND category_id IS NOT NULL) or "
         "(holiday_type='department' AND department_id IS NOT NULL) or "
         "(holiday_type='company' AND mode_company_id IS NOT NULL))",
         "The employee, department, company or employee category of this request is missing. Please make sure that your user login is linked to an employee."),
        ('duration_check', "CHECK ( number_of_days >= 0 )", "The number of days must be greater than 0."),
        # ('plan_unique', 'UNIQUE(accrual_plan_id)', "There is already similar accrual allocation with the same plan"),
    ]

    @api.model
    def _update_accrual(self):
        """
            Method called by the cron task in order to increment the number_of_days when
            necessary.
        """
        # Get the current date to determine the start and end of the accrual period
        today = datetime.combine(fields.Date.today(), time(0, 0, 0))
        allocations = self.search(
            [('allocation_type', '=', 'accrual'), ('state', '=', 'validate'), ('accrual_plan_id', '!=', False),
             '|', ('date_to', '=', False), ('date_to', '>', fields.Datetime.now()),
             '|', ('nextcall', '=', False), ('nextcall', '<', today)])

        # search accural items to see which one must be updated once we have them.
        # to be recalculated, an accural item must be correlated with an active (validated etc) hr.leave.allocation
        for allocation in allocations:
            # First we select all the potential items that could be run
            linked_items = allocation.linked_request_ids.filtered(
                lambda rec: rec.active and (rec.nextcall is False or rec.nextcall <= today.date()))

            # The employee that does not have an accrual_plan_id or if the allocation has no accrual plan, should not be run
            # Calculate the available days for each employee
            # We actually only calculate the added hours for records at the end of their period
            linked_items._increment_accural_items()
            nextcalls = allocation.linked_request_ids.mapped('nextcall')
            # If an employee has an accrual plan_id, then its nextcall dates are false.
            if not nextcalls or not all(nextcalls):
                # At least one item has no nextcall and therefore, we should run the cron job tomorrow.
                # Without that, an employee could see his allocation never calculated when cron job skips him everyday
                nextcall = today + relativedelta(days=1)
            else:
                nextcall = min(nextcalls)
            # if the manager set the plan on employees after the cron, we have to make sure that it will be rerun the next day
            allocation.write({'nextcall': nextcall})

    @api.depends_context('uid')
    def _compute_description(self):
        self.check_access_rights('read')
        self.check_access_rule('read')

        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')

        for allocation in self:
            if is_officer or allocation.employee_id.user_id == self.env.user or allocation.employee_id.leave_manager_id == self.env.user:
                allocation.name = allocation.sudo().private_name
            else:
                allocation.name = '*****'

    def _inverse_description(self):
        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        for allocation in self:
            if is_officer or allocation.employee_id.user_id == self.env.user or allocation.employee_id.leave_manager_id == self.env.user:
                allocation.sudo().private_name = allocation.name

    def _search_description(self, operator, value):
        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        domain = [('private_name', operator, value)]

        if not is_officer:
            domain = expression.AND([domain, [('employee_id.user_id', '=', self.env.user.id)]])

        allocations = self.sudo().search(domain)
        return [('id', 'in', allocations.ids)]

    @api.depends('employee_id', 'holiday_status_id')
    def _compute_leaves(self):
        for allocation in self:
            leave_type = allocation.holiday_status_id.with_context(employee_id=allocation.employee_id.id)
            allocation.max_leaves = leave_type.max_leaves
            allocation.leaves_taken = leave_type.leaves_taken

    @api.depends('extra_days', 'number_of_days')
    def _onchange_extra_days(self):
        for record in self:
            if record.allocation_type == "accrual" and record.extra_days > 0:
                record.number_of_days = record.extra_days
            else:
                record.extra_days = record.number_of_days

    @api.depends('number_of_days')
    def _compute_number_of_days_display(self):
        for allocation in self:
            allocation.number_of_days_display = allocation.number_of_days

    @api.depends('number_of_days', 'employee_id')
    def _compute_number_of_hours_display(self):
        for allocation in self:
            if allocation.number_of_days:
                allocation.number_of_hours_display = allocation.number_of_days * (allocation.employee_id.sudo().resource_id.calendar_id.hours_per_day or HOURS_PER_DAY)
            else:
                allocation.number_of_hours_display = 0.0

    @api.depends('number_of_hours_display', 'number_of_days_display')
    def _compute_duration_display(self):
        for allocation in self:
            allocation.duration_display = '%g %s' % (
                (float_round(allocation.number_of_hours_display, precision_digits=2)
                if allocation.type_request_unit == 'hour'
                else float_round(allocation.number_of_days_display, precision_digits=2)),
                _('hours') if allocation.type_request_unit == 'hour' else _('days'))

    def _compute_agregated_duration(self):
        # Depending on the allocation type, allocation or extradays are displayed
        for regular in self.filtered(lambda al: al.allocation_type == 'regular'):
            regular.write({'aggretated_duration': regular.duration_display})
        for accrual in self.filtered(lambda al: al.allocation_type == 'accrual' and al.holiday_type != 'employee'):
            accrual.write({'aggretated_duration': '%g %s' % (accrual.extra_days, 'Days')})
        for accrual in self.filtered(lambda al: al.allocation_type == 'accrual' and al.holiday_type == 'employee'):
            accrual.write({'aggretated_duration': '%g %s' % (accrual.extra_days + accrual.linked_request_ids.number_of_days, 'Days')})

    @api.depends('state', 'employee_id', 'department_id')
    def _compute_can_reset(self):
        for allocation in self:
            try:
                allocation._check_approval_update('draft')
            except (AccessError, UserError):
                allocation.can_reset = False
            else:
                allocation.can_reset = True

    @api.depends('state', 'employee_id', 'department_id')
    def _compute_can_approve(self):
        for allocation in self:
            try:
                if allocation.state == 'confirm' and allocation.validation_type == 'both':
                    allocation._check_approval_update('validate1')
                else:
                    allocation._check_approval_update('validate')
            except (AccessError, UserError):
                allocation.can_approve = False
            else:
                allocation.can_approve = True

    @api.depends('holiday_type', 'category_id', 'mode_company_id', 'department_id')
    def _compute_from_holiday_type(self):
        for allocation in self:
            if allocation.holiday_type == 'employee':
                if not allocation.employee_id:
                    allocation.employee_id = self.env.user.employee_id
                allocation.mode_company_id = False
                allocation.category_id = False
                employees = allocation.employee_id
                allocation.target = employees.name
            if allocation.holiday_type == 'company':
                allocation.employee_id = False
                if not allocation.mode_company_id:
                    allocation.mode_company_id = self.env.company
                allocation.category_id = False
                employees = self.env['hr.employee'].search([('company_id', '=', allocation.mode_company_id.id)])
                allocation.target = allocation.mode_company_id.name
            elif allocation.holiday_type == 'department':
                allocation.employee_id = False
                allocation.mode_company_id = False
                allocation.category_id = False
                employees = allocation.department_id.member_ids
                allocation.target = allocation.department_id.name
            elif allocation.holiday_type == 'category':
                allocation.employee_id = False
                allocation.mode_company_id = False
                employees = allocation.category_id.employee_ids
                allocation.target = allocation.category_id.name
            elif not allocation.employee_id and not allocation._origin.employee_id:
                allocation.employee_id = self.env.context.get('default_employee_id') or self.env.user.employee_id
                allocation.accrual_plan_id = allocation.employee_id.accrual_plan_id

    @api.depends('holiday_type', 'employee_id')
    def _compute_department_id(self):
        for allocation in self:
            if allocation.holiday_type == 'employee':
                allocation.department_id = allocation.employee_id.department_id
            elif allocation.holiday_type == 'department':
                if not allocation.department_id:
                    allocation.department_id = self.env.user.employee_id.department_id
            elif allocation.holiday_type == 'category':
                allocation.department_id = False


    @api.depends('employee_id')
    def _compute_from_employee_id(self):
        default_holiday_status_id = self._default_holiday_status_id()
        for holiday in self:
            holiday.manager_id = holiday.employee_id and holiday.employee_id.parent_id
            if holiday.employee_id.user_id != self.env.user and holiday._origin.employee_id != holiday.employee_id:
                holiday.holiday_status_id = False
            elif not holiday.holiday_status_id and not holiday._origin.holiday_status_id:
                holiday.holiday_status_id = default_holiday_status_id

    @api.depends('holiday_status_id', 'allocation_type', 'number_of_hours_display', 'number_of_days_display')
    def _compute_from_holiday_status_id(self):
        for allocation in self:
            allocation.number_of_days = allocation.number_of_days_display
            if allocation.type_request_unit == 'hour':
                allocation.number_of_days = allocation.number_of_hours_display / (allocation.employee_id.sudo().resource_calendar_id.hours_per_day or HOURS_PER_DAY)

            # set default values
            if not allocation.number_of_days and not allocation._origin.number_of_days:
                allocation.number_of_days = 0
            if allocation.holiday_status_id.validity_stop and allocation.date_to:
                new_date_to = datetime.combine(allocation.holiday_status_id.validity_stop, time.max)
                if new_date_to < allocation.date_to:
                    allocation.date_to = new_date_to
                allocation.number_of_days = 0

    @api.depends('linked_request_ids', 'state', 'allocation_type')
    def _compute_allocation_item_count(self):
        self.allocation_item_count = 0
        items = self.env['hr.leave.allocation.item'].search([('allocation_id', 'in', self.ids)])
        for allocation in self:
            allocation.allocation_item_count = len(items.filtered(lambda item: item.allocation_id.id == allocation.id))


    def _compute_allocation_item(self):
        """
        This method create the missing accrual items when an employee is added to an accrual plan for example.
        It also archive the non unneeded accrual item when an employee is removed from a plan. We can't unlink the recordq
        to avoid destroying accrued time off.
        :return:
        """
        self.linked_request_ids = False
        for allocation in self.filtered(lambda al: al.state == 'validate'):
            items = self.env['hr.leave.allocation.item'].search([('allocation_id', '=', allocation.id)])
            allocation.write({'linked_request_ids': items})

    def _update_allocation_item(self):
        """
        This method creates the missing accrual items upon allocation aproval or when a new employee is created and added
        in a category/department/company whose time off are managed by an allocation
        """
        for allocation in self:
            # We need to create accrual items when employee is added to a category, department, company
            all_allocation_item_ids = self.env['hr.leave.allocation.item'].with_context(active_test=False).search([('allocation_id', '=', allocation.id)])
            active_allocation_item_ids = self.env['hr.leave.allocation.item'].search([('allocation_id', '=', allocation.id)])
            employees_items = active_allocation_item_ids.mapped('employee_id')
            new_items_ids = discarded_items = self.env['hr.leave.allocation.item']
            if allocation.holiday_type == 'employee':
                employees = allocation.employee_id
            elif allocation.holiday_type == 'category':
                employees = allocation.category_id.employee_ids
            elif allocation.holiday_type == 'department':
                employees = allocation.department_id.member_ids
            else:
                employees = self.env['hr.employee'].search([('company_id', '=', self.mode_company_id.id)])

            if employees_items != employees:
                # looking for employee that should have an accrual item but don't
                missing_employee = employees.filtered(lambda h: h.id not in employees_items.ids)
                create_values, updatable_items = allocation._prepare_holiday_values(missing_employee)
                new_items_ids = self.env['hr.leave.allocation.item'].sudo().create(create_values)
                # allocation.write({'linked_request_ids': [(4, 0, item_id) for item_id in new_items_ids.ids]})
                updatable_items.write({'active': True})
                if allocation.accrual_plan_id:
                    missing_employee._update_accrual_plan(allocation.accrual_plan_id, addition=True)
                # Looking for employee that have an item but should not
                # arj fixme: what happens to refused allocation or when they are put back in draft ??
                # Should we delete all corresponding items ?
                discarded_employee = employees_items.filtered(lambda h: h.id not in employees.ids)
                discarded_items = all_allocation_item_ids.filtered(lambda item: item.employee_id.id in discarded_employee.ids)
                discarded_items.write({'active': False})
                discarded_employee._update_accrual_plan(allocation.accrual_plan_id, addition=False)

            all_items = all_allocation_item_ids | new_items_ids | discarded_items
            allocation.write({'linked_request_ids': all_items})

    ####################################################
    # ORM Overrides methods
    ####################################################

    def name_get(self):
        res = []
        for allocation in self:
            time_factor = HOURS_PER_DAY
            if allocation.holiday_type == 'company':
                target = allocation.mode_company_id.name
            elif allocation.holiday_type == 'department':
                target = allocation.department_id.name
            elif allocation.holiday_type == 'category':
                target = allocation.category_id.name
            else:
                target = allocation.employee_id.sudo().name
                time_factor = allocation.employee_id.resource_calendar_id.hours_per_day or HOURS_PER_DAY

            total_days = allocation.number_of_days + allocation.extra_days
            total_hours = allocation.number_of_hours_display + (allocation.extra_days * time_factor)
            res.append(
                (allocation.id,
                 _("Allocation of %(allocation_name)s : %(duration).2f %(duration_type)s to %(person)s",
                   allocation_name=allocation.holiday_status_id.sudo().name,
                   duration=total_hours if allocation.type_request_unit == 'hour' else total_days,
                   duration_type='hours' if allocation.type_request_unit == 'hour' else 'days',
                   person=target
                ))
            )
        return res

    def add_follower(self, employee_id):
        employee = self.env['hr.employee'].browse(employee_id)
        if employee.user_id:
            self.message_subscribe(partner_ids=employee.user_id.partner_id.ids)

    @api.constrains('holiday_status_id')
    def _check_leave_type_validity(self):
        for allocation in self:
            if allocation.holiday_status_id.validity_stop:
                vstop = allocation.holiday_status_id.validity_stop
                today = fields.Date.today()

                if vstop < today:
                    raise ValidationError(_(
                        'You can allocate %(allocation_type)s only before %(date)s.',
                        allocation_type=allocation.holiday_status_id.display_name,
                        date=allocation.holiday_status_id.validity_stop
                    ))

    @api.model
    def create(self, values):
        """ Override to avoid automatic logging of creation """
        employee_id = values.get('employee_id', False)
        if not values.get('department_id'):
            values.update({'department_id': self.env['hr.employee'].browse(employee_id).department_id.id})
        if values.get('date_from') and fields.Date.from_string(values.get('date_from')) < fields.Date.context_today(self):
            raise ValidationError(_("The accrual start date must be today or after. However, it is possible to indicate "
                                    "an initial number of allocated days."))
        holiday = super(HolidaysAllocation, self.with_context(mail_create_nosubscribe=True)).create(values)
        holiday.add_follower(employee_id)
        if holiday.validation_type == 'hr':
            holiday.message_subscribe(partner_ids=(holiday.employee_id.parent_id.user_id.partner_id | holiday.employee_id.leave_manager_id.partner_id).ids)
        if not self._context.get('import_file'):
            holiday.activity_update()
        return holiday

    def write(self, values):
        employee_id = values.get('employee_id', False)
        if values.get('state'):
            self._check_approval_update(values['state'])
        if values.get('date_from') and fields.Date.from_string(values.get('date_from')) < fields.Date.context_today(self):
            raise ValidationError(_("The accrual start date must be today of after"))
        result = super(HolidaysAllocation, self).write(values)
        self.add_follower(employee_id)
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_if_correct_states(self):
        state_description_values = {elem[0]: elem[1] for elem in self._fields['state']._description_selection(self.env)}
        for holiday in self.filtered(lambda holiday: holiday.state not in ['draft', 'cancel', 'confirm']):
            raise UserError(_('You cannot delete an allocation request which is in %s state.') % (state_description_values.get(holiday.state),))

    def _get_mail_redirect_suggested_company(self):
        return self.holiday_status_id.company_id

    ####################################################
    # Business methods
    ####################################################

    def _prepare_holiday_values(self, employees):
        self.ensure_one()
        create_result = []
        update_result = self.env['hr.leave.allocation.item']
        items = self.with_context(active_test=False).linked_request_ids
        for employee in employees:
            existing_item = items.filtered(lambda i: i.allocation_id.id == self.id and i.employee_id.id == employee.id and i.accrual_plan_id.id == self.accrual_plan_id.id)
            if not existing_item:
                if self.allocation_type == 'regular':
                    number_of_days = self.number_of_days
                else:
                    number_of_days = 0
                create_result.append({
                    'name': f"{self.name} {employee.name}",
                    'allocation_id': self.id,
                    'employee_id': employee.id,
                    'accrual_plan_id': self.accrual_plan_id.id,
                    'number_of_days': number_of_days,

                })
            else:
                # There is an item that was probably archived
                update_result |= existing_item

        return create_result, update_result

    def action_draft(self):
        if any(holiday.state not in ['confirm', 'refuse'] for holiday in self):
            raise UserError(_('Allocation request state must be "Refused" or "To Approve" in order to be reset to Draft.'))
        self.write({
            'state': 'draft',
            'first_approver_id': False,
            'second_approver_id': False,
        })
        linked_requests = self.mapped('linked_request_ids')
        if linked_requests:
            linked_requests.unlink()
        self.activity_update()
        return True

    def action_confirm(self):
        if self.filtered(lambda holiday: holiday.state != 'draft'):
            raise UserError(_('Allocation request must be in Draft state ("To Submit") in order to confirm it.'))
        res = self.write({'state': 'confirm'})
        self.activity_update()
        return res

    def action_approve(self):
        # if validation_type == 'both': this method is the first approval approval
        # if validation_type != 'both': this method calls action_validate() below
        if any(holiday.state != 'confirm' for holiday in self):
            raise UserError(_('Allocation request must be confirmed ("To Approve") in order to approve it.'))

        current_employee = self.env.user.employee_id

        self.filtered(lambda hol: hol.validation_type == 'both').write({'state': 'validate1', 'first_approver_id': current_employee.id})
        self.filtered(lambda hol: not hol.validation_type == 'both').action_validate()
        self.activity_update()

    def action_validate(self):
        current_employee = self.env.user.employee_id
        for holiday in self:
            if holiday.state not in ['confirm', 'validate1']:
                raise UserError(_('Allocation request must be confirmed in order to approve it.'))

            holiday.write({'state': 'validate'})
            if holiday.validation_type == 'both':
                holiday.write({'second_approver_id': current_employee.id})
            else:
                holiday.write({'first_approver_id': current_employee.id})

            holiday._update_allocation_item()
        self.activity_update()
        return True

    def action_refuse(self):
        current_employee = self.env.user.employee_id
        if any(holiday.state not in ['confirm', 'validate', 'validate1'] for holiday in self):
            raise UserError(_('Allocation request must be confirmed or validated in order to refuse it.'))

        validated_holidays = self.filtered(lambda hol: hol.state == 'validate1')
        validated_holidays.write({'state': 'refuse', 'first_approver_id': current_employee.id})
        (self - validated_holidays).write({'state': 'refuse', 'second_approver_id': current_employee.id})
        self.activity_update()
        return True

    def action_related_items(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("hr_holidays.hr_holidays_allocation_item")
        action['domain'] = [('id', 'in', self.with_context(active_test=False).linked_request_ids.ids)]
        return action

    def _check_approval_update(self, state):
        """ Check if target state is achievable. """
        if self.env.is_superuser():
            return
        current_employee = self.env.user.employee_id
        if not current_employee:
            return
        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        is_manager = self.env.user.has_group('hr_holidays.group_hr_holidays_manager')
        for holiday in self:
            val_type = holiday.holiday_status_id.sudo().allocation_validation_type
            if state == 'confirm':
                continue

            if state == 'draft':
                if holiday.employee_id != current_employee and not is_manager:
                    raise UserError(_('Only a time off Manager can reset other people allocation.'))
                continue

            if not is_officer and self.env.user != holiday.employee_id.leave_manager_id:
                raise UserError(_('Only a time off Officer/Responsible or Manager can approve or refuse time off requests.'))

            if is_officer or self.env.user == holiday.employee_id.leave_manager_id:
                # use ir.rule based first access check: department, members, ... (see security.xml)
                holiday.check_access_rule('write')

            if holiday.employee_id == current_employee and not is_manager:
                raise UserError(_('Only a time off Manager can approve its own requests.'))

            if (state == 'validate1' and val_type == 'both') or (state == 'validate' and val_type == 'manager'):
                if self.env.user == holiday.employee_id.leave_manager_id and self.env.user != holiday.employee_id.user_id:
                    continue
                manager = holiday.employee_id.parent_id or holiday.employee_id.department_id.manager_id
                if (manager != current_employee) and not is_manager:
                    raise UserError(_('You must be either %s\'s manager or time off manager to approve this time off') % (holiday.employee_id.name))

            if state == 'validate' and val_type == 'both':
                if not is_officer:
                    raise UserError(_('Only a Time off Approver can apply the second approval on allocation requests.'))

    # ------------------------------------------------------------
    # Activity methods
    # ------------------------------------------------------------

    def _get_responsible_for_approval(self):
        self.ensure_one()
        responsible = self.env.user

        if self.validation_type == 'manager' or (self.validation_type == 'both' and self.state == 'confirm'):
            if self.employee_id.leave_manager_id:
                responsible = self.employee_id.leave_manager_id
        elif self.validation_type == 'hr' or (self.validation_type == 'both' and self.state == 'validate1'):
            if self.holiday_status_id.responsible_id:
                responsible = self.holiday_status_id.responsible_id

        return responsible

    def activity_update(self):
        to_clean, to_do = self.env['hr.leave.allocation'], self.env['hr.leave.allocation']
        for allocation in self:
            note = _(
                'New Allocation Request created by %(user)s: %(count)s Days of %(allocation_type)s',
                user=allocation.create_uid.name,
                count=allocation.number_of_days,
                allocation_type=allocation.holiday_status_id.name
            )
            if allocation.state == 'draft':
                to_clean |= allocation
            elif allocation.state == 'confirm':
                allocation.activity_schedule(
                    'hr_holidays.mail_act_leave_allocation_approval',
                    note=note,
                    user_id=allocation.sudo()._get_responsible_for_approval().id or self.env.user.id)
            elif allocation.state == 'validate1':
                allocation.activity_feedback(['hr_holidays.mail_act_leave_allocation_approval'])
                allocation.activity_schedule(
                    'hr_holidays.mail_act_leave_allocation_second_approval',
                    note=note,
                    user_id=allocation.sudo()._get_responsible_for_approval().id or self.env.user.id)
            elif allocation.state == 'validate':
                to_do |= allocation
            elif allocation.state == 'refuse':
                to_clean |= allocation
        if to_clean:
            to_clean.activity_unlink(['hr_holidays.mail_act_leave_allocation_approval', 'hr_holidays.mail_act_leave_allocation_second_approval'])
        if to_do:
            to_do.activity_feedback(['hr_holidays.mail_act_leave_allocation_approval', 'hr_holidays.mail_act_leave_allocation_second_approval'])

    ####################################################
    # Messaging methods
    ####################################################

    def _track_subtype(self, init_values):
        if 'state' in init_values and self.state == 'validate':
            allocation_notif_subtype_id = self.holiday_status_id.allocation_notif_subtype_id
            return allocation_notif_subtype_id or self.env.ref('hr_holidays.mt_leave_allocation')
        return super(HolidaysAllocation, self)._track_subtype(init_values)

    def _notify_get_groups(self, msg_vals=None):
        """ Handle HR users and officers recipients that can validate or refuse holidays
        directly from email. """
        groups = super(HolidaysAllocation, self)._notify_get_groups(msg_vals=msg_vals)
        msg_vals = msg_vals or {}

        self.ensure_one()
        hr_actions = []
        if self.state == 'confirm':
            app_action = self._notify_get_action_link('controller', controller='/allocation/validate', **msg_vals)
            hr_actions += [{'url': app_action, 'title': _('Approve')}]
        if self.state in ['confirm', 'validate', 'validate1']:
            ref_action = self._notify_get_action_link('controller', controller='/allocation/refuse', **msg_vals)
            hr_actions += [{'url': ref_action, 'title': _('Refuse')}]

        holiday_user_group_id = self.env.ref('hr_holidays.group_hr_holidays_user').id
        new_group = (
            'group_hr_holidays_user', lambda pdata: pdata['type'] == 'user' and holiday_user_group_id in pdata['groups'], {
                'actions': hr_actions,
            })

        return [new_group] + groups

    def message_subscribe(self, partner_ids=None, subtype_ids=None):
        # due to record rule can not allow to add follower and mention on validated leave so subscribe through sudo
        if self.state in ['validate', 'validate1']:
            self.check_access_rights('read')
            self.check_access_rule('read')
            return super(HolidaysAllocation, self.sudo()).message_subscribe(partner_ids=partner_ids, subtype_ids=subtype_ids)
        return super(HolidaysAllocation, self).message_subscribe(partner_ids=partner_ids, subtype_ids=subtype_ids)
