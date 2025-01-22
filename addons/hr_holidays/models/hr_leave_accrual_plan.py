# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from odoo.addons.hr_holidays.models.hr_leave_accrual_plan_level import _get_selection_days

DAY_SELECT_VALUES = [str(i) for i in range(1, 29)] + ['last']
DAY_SELECT_SELECTION_NO_LAST = tuple(zip(DAY_SELECT_VALUES, (str(i) for i in range(1, 29))))


class HrLeaveAccrualPlan(models.Model):
    _name = 'hr.leave.accrual.plan'
    _description = "Accrual Plan"

    active = fields.Boolean(default=True)
    name = fields.Char('Name')
    time_off_type_id = fields.Many2one('hr.leave.type', string="Time Off Type",
        check_company=True, index='btree_not_null',
        help="""Specify if this accrual plan can only be used with this Time Off Type.
                Leave empty if this accrual plan can be used with any Time Off Type.""")
    employees_count = fields.Integer("Employees", compute='_compute_employee_count')
    level_ids = fields.One2many('hr.leave.accrual.level', 'accrual_plan_id', copy=True, string="Milestone")
    allocation_ids = fields.One2many('hr.leave.allocation', 'accrual_plan_id')
    company_id = fields.Many2one('res.company', string='Company', domain=lambda self: [('id', 'in', self.env.companies.ids)],
        compute="_compute_company_id", store="True", readonly=False)
    transition_mode = fields.Selection([
        ('immediately', 'Immediately'),
        ('end_of_accrual', "After this accrual's period")],
        string="Milestone Transition", default="immediately", required=True)
    show_transition_mode = fields.Boolean(compute='_compute_show_transition_mode')
    is_based_on_worked_time = fields.Boolean("Based on worked time", compute="_compute_is_based_on_worked_time", store=True, readonly=False,
                                             help="Only excludes requests where the time off type is set as unpaid kind of.")
    accrued_gain_time = fields.Selection([
        ("start", "At the start of the accrual period"),
        ("end", "At the end of the accrual period")],
        default="end", required=True)
    is_carryover = fields.Boolean(default=True, store=True)
    carryover_date = fields.Selection([
        ("year_start", "At the start of the year"),
        ("allocation", "At the allocation date"),
        ("other", "Custom date")],
        default="year_start", required=True, string="Carry-Over Time")
    carryover_day = fields.Integer(default=1, store=True)
    carryover_day_display = fields.Selection(
        _get_selection_days, compute='_compute_carryover_day_display', inverse='_inverse_carryover_day_display')
    carryover_month = fields.Selection([
        ("jan", "January"),
        ("feb", "February"),
        ("mar", "March"),
        ("apr", "April"),
        ("may", "May"),
        ("jun", "June"),
        ("jul", "July"),
        ("aug", "August"),
        ("sep", "September"),
        ("oct", "October"),
        ("nov", "November"),
        ("dec", "December")
    ], default="jan")
    added_value_type = fields.Selection([('day', 'Days'), ('hour', 'Hours')], default="day", store=True)
    summary = fields.Html(readonly=True, compute='_compute_summary')

    @api.depends('transition_mode', 'show_transition_mode', 'is_based_on_worked_time', 'accrued_gain_time',
                 'is_carryover', 'carryover_date', 'carryover_day_display', 'carryover_month')
    def _compute_summary(self):
        for plan in self:
            carryover_day = str(
                dict(plan._fields["carryover_day_display"].get_description(plan.env).get("selection"))
                .get(plan.carryover_day_display)) if plan.carryover_day_display else _("[select a day]")
            carryover_month = str(
                dict(plan._fields["carryover_month"].get_description(plan.env).get("selection"))
                .get(plan.carryover_month)) if plan.carryover_month else _("[select a month]")

            if plan.accrued_gain_time == "start":
                if plan.is_based_on_worked_time:
                    start_or_end_worked_time = _(
                        "This accrual plan is accrued at the <b>start of each period</b>,\
                         <b>based on the worked time.</b>")
                else:
                    start_or_end_worked_time = _("This accrual plan is accrued at the <b>start of each period</b>,\
                     <b>based on the whole calendar days.</b>")
            else:
                if plan.is_based_on_worked_time:
                    start_or_end_worked_time = _(
                        "This accrual plan is accrued at the <b>end of each period</b>,\
                         <b>based on the worked time.</b>")
                else:
                    start_or_end_worked_time = _("This accrual plan is accrued at the <b>end of each period</b>,\
                     <b>based on the whole calendar days.</b>")
            if plan.is_carryover:
                if plan.carryover_date == "year_start":
                    carryover = _("<br/>Accrued days <b>are carried over</b> from year to year,\
                     <b>at the start of the year.</b>")
                elif plan.carryover_date == "allocation":
                    carryover = _("<br/>Accrued days <b>are carried over</b> from year to year,\
                     <b>at the allocation date.</b>")
                else:
                    carryover = _("<br/>Accrued days <b>are carried over</b> from year to year,\
                     <b>at the %(day)s of %(month)s.</b>", day=carryover_day, month=carryover_month)
            else:
                carryover = _("<br/>Accrued days <b>are not carried over</b> from year to year.")
            if plan.show_transition_mode:
                if plan.transition_mode == "immediately":
                    transition_mode = _(
                        "<br/>If an accrual level changes in the middle of a pay period, <b>employees are immediately \
                        placed on the next accrual level</b> on the exact date during the current pay period.")
                else:
                    transition_mode = _(
                        "<br/>If an accrual level changes in the middle of a pay period, <b>employees are placed on \
                        the next accrual level on the next pay period.</b>")
            else:
                transition_mode = ""

            plan.summary = start_or_end_worked_time + carryover + transition_mode

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

    @api.depends("carryover_day")
    def _compute_carryover_day_display(self):
        days_select = _get_selection_days(self)
        for plan in self:
            plan.carryover_day_display = days_select[min(plan.carryover_day - 1, 28)][0]

    def _inverse_carryover_day_display(self):
        for plan in self:
            if plan.carryover_day_display == 'last':
                plan.carryover_day = 31
            elif int(plan.carryover_day_display) in range(1,29):
                plan.carryover_day = DAY_SELECT_VALUES.index(plan.carryover_day_display) + 1
            else:
                plan.carryover_day = False

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
        action = self.env.ref('hr_holidays.action_open_accrual_plan_level').read()[0]
        action['name'] = _('New Milestone')
        action['context'] = dict(self.env.context)
        action["context"].update({
            'new': True,
            'is_carryover': self.is_carryover,
            'accrued_gain_time': self.accrued_gain_time,
            'can_modify_value_type': not self.time_off_type_id and not self.level_ids,
            'added_value_type': self.added_value_type,
        })
        return action

    def action_open_accrual_plan_level(self,level_id):
        action = self.env.ref('hr_holidays.action_open_accrual_plan_level').read()[0]
        action.update({
            'name': _('Milestone Edition'),
            'res_id': level_id,
        })
        return action

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

    def create(self, vals_list):
        res = super().create(vals_list)
        if not 'name' in res or not res['name']:
            res.write({'name': "My Plan #" + str(res.id)})
        return res
