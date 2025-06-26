# Part of Odoo. See LICENSE file for full copyright and licensing details.
from calendar import monthrange

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from odoo.addons.hr_holidays.models.hr_leave_accrual_plan_level import _get_selection_days


class HrLeaveAccrualPlan(models.Model):
    _name = 'hr.leave.accrual.plan'
    _description = "Accrual Plan"

    active = fields.Boolean(default=True)
    name = fields.Char('Name', required=True)
    time_off_type_id = fields.Many2one('hr.leave.type', string="Time Off Type",
        check_company=True, index='btree_not_null',
        help="""Specify if this accrual plan can only be used with this Time Off Type.
                Leave empty if this accrual plan can be used with any Time Off Type.""")
    employees_count = fields.Integer("Employees", compute='_compute_employee_count')
    level_ids = fields.One2many('hr.leave.accrual.level', 'accrual_plan_id', copy=True, string="Milestones")
    allocation_ids = fields.One2many('hr.leave.allocation', 'accrual_plan_id',
        export_string_translation=False)
    company_id = fields.Many2one('res.company', string='Company', domain=lambda self: [('id', 'in', self.env.companies.ids)],
        compute="_compute_company_id", store="True", readonly=False)
    transition_mode = fields.Selection([
        ('immediately', 'Immediately'),
        ('end_of_accrual', "After this accrual's period")],
        export_string_translation=False, default="immediately", required=True)
    show_transition_mode = fields.Boolean(compute='_compute_show_transition_mode', export_string_translation=False)
    is_based_on_worked_time = fields.Boolean(compute="_compute_is_based_on_worked_time", store=True, readonly=False,
        export_string_translation=False,
        help="Only excludes requests where the time off type is set as unpaid kind of.")
    accrued_gain_time = fields.Selection([
        ("start", "At the start of the accrual period"),
        ("end", "At the end of the accrual period")],
        export_string_translation=False,
        default="end", required=True)
    can_be_carryover = fields.Boolean(export_string_translation=False)
    carryover_date = fields.Selection([
        ("year_start", "At the start of the year"),
        ("allocation", "At the allocation date"),
        ("other", "Custom date")],
        export_string_translation=False,
        default="year_start", required=True, string="Carry-Over Time")
    carryover_day = fields.Selection(
        _get_selection_days, compute='_compute_carryover_day',
        export_string_translation=False, store=True, readonly=False, default='1')
    carryover_month = fields.Selection([
        ("1", "January"),
        ("2", "February"),
        ("3", "March"),
        ("4", "April"),
        ("5", "May"),
        ("6", "June"),
        ("7", "July"),
        ("8", "August"),
        ("9", "September"),
        ("10", "October"),
        ("11", "November"),
        ("12", "December")
    ], export_string_translation=False, default=lambda self: str((fields.Date.today()).month))
    added_value_type = fields.Selection([('day', 'Days'), ('hour', 'Hours')],
        export_string_translation=False, default="day", store=True)

    @api.depends('level_ids')
    def _compute_show_transition_mode(self):
        for plan in self:
            plan.show_transition_mode = len(plan.level_ids) > 1

    level_count = fields.Integer('Levels', compute='_compute_level_count')

    @api.depends('level_ids')
    def _compute_level_count(self):
        level_read_group = self.env['hr.leave.accrual.level']._read_group(
            [('accrual_plan_id', 'in', self.ids)],
            groupby=['accrual_plan_id'],
            aggregates=['__count'],
        )
        mapped_count = {accrual_plan.id: count for accrual_plan, count in level_read_group}
        for plan in self:
            plan.level_count = mapped_count.get(plan.id, 0)

    @api.depends('allocation_ids')
    def _compute_employee_count(self):
        allocations_read_group = self.env['hr.leave.allocation']._read_group(
            [('accrual_plan_id', 'in', self.ids)],
            ['accrual_plan_id'],
            ['employee_id:count_distinct'],
        )
        allocations_dict = {accrual_plan.id: count for accrual_plan, count in allocations_read_group}
        for plan in self:
            plan.employees_count = allocations_dict.get(plan.id, 0)

    @api.depends('time_off_type_id.company_id')
    def _compute_company_id(self):
        for accrual_plan in self:
            if accrual_plan.time_off_type_id:
                accrual_plan.company_id = accrual_plan.time_off_type_id.company_id
            else:
                accrual_plan.company_id = self.env.company

    @api.depends("accrued_gain_time")
    def _compute_is_based_on_worked_time(self):
        for plan in self:
            if plan.accrued_gain_time == "start":
                plan.is_based_on_worked_time = False

    @api.depends("carryover_month")
    def _compute_carryover_day(self):
        for plan in self:
            # 2020 is a leap year, so monthrange(2020, february) will return [2, 29]
            plan.carryover_day = str(min(monthrange(2020, int(plan.carryover_month))[1], int(plan.carryover_day)))

    def action_open_accrual_plan_employees(self):
        self.ensure_one()
        return {
            'name': _("Accrual Plan's Employees"),
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,list,form',
            'res_model': 'hr.employee',
            'domain': [('id', 'in', self.allocation_ids.employee_id.ids)],
        }

    def action_create_accrual_plan_level(self):
        return {
            'name': self.env._('New Milestone'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.accrual.level',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'view_id': self.env.ref('hr_holidays.hr_accrual_level_view_form').id,
            'target': 'new',
            'context': dict(
                self.env.context,
                new=True,
                default_can_be_carryover=self.can_be_carryover,
                default_accrued_gain_time=self.accrued_gain_time,
                default_can_modify_value_type=not self.time_off_type_id and not self.level_ids,
                default_added_value_type=self.added_value_type,
            ),
        }

    def action_open_accrual_plan_level(self, level_id):
        return {
            'name': self.env._('Milestone Edition'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.accrual.level',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'new',
            'res_id': level_id,
        }

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=self.env._("%s (copy)", plan.name)) for plan, vals in zip(self, vals_list)]

    @api.ondelete(at_uninstall=False)
    def _prevent_used_plan_unlink(self):
        domain = [
            ('allocation_type', '=', 'accrual'),
            ('accrual_plan_id', 'in', self.ids),
            ('state', 'not in', ('cancel', 'refuse')),
        ]
        if self.env['hr.leave.allocation'].search_count(domain):
            raise ValidationError(_(
                "Some of the accrual plans you're trying to delete are linked to an existing allocation. Delete or cancel them first."
            ))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name", False):
                vals['name'] = self.env._("Unnamed Plan")
        return super().create(vals_list)
