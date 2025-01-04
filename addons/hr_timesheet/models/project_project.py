# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import RedirectWarning, ValidationError
from odoo.tools import SQL
from odoo.tools.translate import _


class ProjectProject(models.Model):
    _inherit = "project.project"

    allow_timesheets = fields.Boolean(
        "Timesheets", compute='_compute_allow_timesheets', store=True, readonly=False,
        default=True)
    account_id = fields.Many2one(
        # note: replaces ['|', ('company_id', '=', False), ('company_id', '=', company_id)]
        domain="""[
            '|', ('company_id', '=', False), ('company_id', '=?', company_id),
            ('partner_id', '=?', partner_id),
        ]"""
    )
    analytic_account_active = fields.Boolean("Active Account", related="account_id.active", export_string_translation=False)

    timesheet_ids = fields.One2many('account.analytic.line', 'project_id', 'Associated Timesheets', export_string_translation=False)
    timesheet_encode_uom_id = fields.Many2one('uom.uom', compute='_compute_timesheet_encode_uom_id', export_string_translation=False)
    total_timesheet_time = fields.Integer(
        compute='_compute_total_timesheet_time', groups='hr_timesheet.group_hr_timesheet_user',
        string="Total number of time (in the proper UoM) recorded in the project, rounded to the unit.",
        compute_sudo=True, export_string_translation=False)
    encode_uom_in_days = fields.Boolean(compute='_compute_encode_uom_in_days', export_string_translation=False)
    is_internal_project = fields.Boolean(compute='_compute_is_internal_project', search='_search_is_internal_project', export_string_translation=False)
    remaining_hours = fields.Float(compute='_compute_remaining_hours', string='Time Remaining', compute_sudo=True)
    is_project_overtime = fields.Boolean('Project in Overtime', compute='_compute_remaining_hours', search='_search_is_project_overtime', compute_sudo=True, export_string_translation=False)
    allocated_hours = fields.Float(string='Allocated Time')
    effective_hours = fields.Float(string='Time Spent', compute='_compute_remaining_hours', compute_sudo=True)

    def _compute_encode_uom_in_days(self):
        self.encode_uom_in_days = self.env.company.timesheet_encode_uom_id == self.env.ref('uom.product_uom_day')

    @api.depends('company_id', 'company_id.timesheet_encode_uom_id')
    @api.depends_context('company')
    def _compute_timesheet_encode_uom_id(self):
        for project in self:
            project.timesheet_encode_uom_id = project.company_id.timesheet_encode_uom_id or self.env.company.timesheet_encode_uom_id

    @api.depends('account_id')
    def _compute_allow_timesheets(self):
        without_account = self.filtered(lambda t: t._origin and not t.account_id)
        without_account.update({'allow_timesheets': False})

    @api.depends('company_id')
    def _compute_is_internal_project(self):
        for project in self:
            project.is_internal_project = project == project.company_id.internal_project_id

    @api.model
    def _search_is_internal_project(self, operator, value):
        if not isinstance(value, bool):
            raise ValueError(_('Invalid value: %s', value))
        if operator not in ['=', '!=']:
            raise ValueError(_('Invalid operator: %s', operator))

        Company = self.env['res.company']
        sql = Company._where_calc(
            [('internal_project_id', '!=', False)], active_test=False
        ).subselect("internal_project_id")
        if (operator == '=' and value is True) or (operator == '!=' and value is False):
            operator_new = 'in'
        else:
            operator_new = 'not in'
        return [('id', operator_new, sql)]

    @api.depends('allow_timesheets', 'timesheet_ids.unit_amount', 'allocated_hours')
    def _compute_remaining_hours(self):
        timesheets_read_group = self.env['account.analytic.line']._read_group(
            [('project_id', 'in', self.ids)],
            ['project_id'],
            ['unit_amount:sum'],
        )
        timesheet_time_dict = {project.id: unit_amount_sum for project, unit_amount_sum in timesheets_read_group}
        for project in self:
            project.effective_hours = round(timesheet_time_dict.get(project.id, 0.0), 2)
            project.remaining_hours = project.allocated_hours - project.effective_hours
            project.is_project_overtime = project.remaining_hours < 0

    @api.model
    def _search_is_project_overtime(self, operator, value):
        if not isinstance(value, bool):
            raise ValueError(_('Invalid value: %s', value))
        if operator not in ['=', '!=']:
            raise ValueError(_('Invalid operator: %s', operator))

        sql = SQL("""(
            SELECT Project.id
              FROM project_project AS Project
              JOIN project_task AS Task
                ON Project.id = Task.project_id
             WHERE Project.allocated_hours > 0
               AND Project.allow_timesheets = TRUE
               AND Task.parent_id IS NULL
               AND Task.state IN ('01_in_progress', '02_changes_requested', '03_approved', '04_waiting_normal')
          GROUP BY Project.id
            HAVING Project.allocated_hours - SUM(Task.effective_hours) < 0
        )""")
        if (operator == '=' and value is True) or (operator == '!=' and value is False):
            operator_new = 'in'
        else:
            operator_new = 'not in'
        return [('id', operator_new, sql)]

    @api.constrains('allow_timesheets', 'account_id')
    def _check_allow_timesheet(self):
        for project in self:
            if project.allow_timesheets and not project.account_id:
                project_plan, _other_plans = self.env['account.analytic.plan']._get_all_plans()
                raise ValidationError(_(
                    "To use the timesheets feature, you need an analytic account for your project. Please set one up in the plan '%(plan_name)s' or turn off the timesheets feature.",
                    plan_name=project_plan.name
                ))

    @api.depends('timesheet_ids', 'timesheet_encode_uom_id')
    def _compute_total_timesheet_time(self):
        timesheets_read_group = self.env['account.analytic.line']._read_group(
            [('project_id', 'in', self.ids)],
            ['project_id', 'product_uom_id'],
            ['unit_amount:sum'],
        )
        timesheet_time_dict = defaultdict(list)
        for project, product_uom, unit_amount_sum in timesheets_read_group:
            timesheet_time_dict[project.id].append((product_uom, unit_amount_sum))

        for project in self:
            # Timesheets may be stored in a different unit of measure, so first
            # we convert all of them to the reference unit
            # if the timesheet has no product_uom_id then we take the one of the project
            total_time = 0.0
            for product_uom, unit_amount in timesheet_time_dict[project.id]:
                factor = (product_uom or project.timesheet_encode_uom_id).factor
                total_time += unit_amount * (1.0 if project.encode_uom_in_days else factor)
            # Now convert to the proper unit of measure set in the settings
            total_time /= project.timesheet_encode_uom_id.factor
            project.total_timesheet_time = int(round(total_time))

    @api.model_create_multi
    def create(self, vals_list):
        """ Create an analytic account if project allow timesheet and don't provide one
            Note: create it before calling super() to avoid raising the ValidationError from _check_allow_timesheet
        """
        defaults = self.default_get(['allow_timesheets', 'account_id'])
        analytic_accounts_vals = [
            vals for vals in vals_list
            if (
                vals.get('allow_timesheets', defaults.get('allow_timesheets')) and
                not vals.get('account_id', defaults.get('account_id'))
            )
        ]

        if analytic_accounts_vals:
            analytic_accounts = self.env['account.analytic.account'].create(self._get_values_analytic_account_batch(analytic_accounts_vals))
            for vals, analytic_account in zip(analytic_accounts_vals, analytic_accounts):
                vals['account_id'] = analytic_account.id
        return super().create(vals_list)

    def write(self, values):
        # create the AA for project still allowing timesheet
        if values.get('allow_timesheets') and not values.get('account_id'):
            project_wo_account = self.filtered(lambda project: not project.account_id)
            if project_wo_account:
                project_wo_account._create_analytic_account()
        return super().write(values)

    @api.depends('is_internal_project', 'company_id')
    @api.depends_context('allowed_company_ids')
    def _compute_display_name(self):
        super()._compute_display_name()
        if len(self.env.context.get('allowed_company_ids') or []) <= 1:
            return

        for project in self:
            if project.is_internal_project:
                project.display_name = f'{project.display_name} - {project.company_id.name}'

    @api.model
    def _init_data_analytic_account(self):
        self.search([('account_id', '=', False), ('allow_timesheets', '=', True)])._create_analytic_account()

    @api.ondelete(at_uninstall=False)
    def _unlink_except_contains_entries(self):
        """
        If some projects to unlink have some timesheets entries, these
        timesheets entries must be unlinked first.
        In this case, a warning message is displayed through a RedirectWarning
        and allows the user to see timesheets entries to unlink.
        """
        projects_with_timesheets = self.filtered(lambda p: p.timesheet_ids)
        if projects_with_timesheets:
            if len(projects_with_timesheets) > 1:
                warning_msg = _("These projects have some timesheet entries referencing them. Before removing these projects, you have to remove these timesheet entries.")
            else:
                warning_msg = _("This project has some timesheet entries referencing it. Before removing this project, you have to remove these timesheet entries.")
            raise RedirectWarning(
                warning_msg, self.env.ref('hr_timesheet.timesheet_action_project').id,
                _('See timesheet entries'), {'active_ids': projects_with_timesheets.ids})

    @api.model
    def get_create_edit_project_ids(self):
        return []

    def _convert_project_uom_to_timesheet_encode_uom(self, time):
        uom_from = self.company_id.project_time_mode_id
        uom_to = self.env.company.timesheet_encode_uom_id
        return round(uom_from._compute_quantity(time, uom_to, raise_if_failure=False), 2)

    def action_project_timesheets(self):
        action = self.env['ir.actions.act_window']._for_xml_id('hr_timesheet.act_hr_timesheet_line_by_project')
        action['display_name'] = _("%(name)s's Timesheets", name=self.name)
        return action

    # ----------------------------
    #  Project Updates
    # ----------------------------

    def _get_stat_buttons(self):
        buttons = super()._get_stat_buttons()
        if not self.allow_timesheets or not self.env.user.has_group("hr_timesheet.group_hr_timesheet_user"):
            return buttons

        encode_uom = self.env.company.timesheet_encode_uom_id
        uom_ratio = self.env.ref('uom.product_uom_hour').factor / encode_uom.factor

        allocated = self.allocated_hours / uom_ratio
        effective = self.total_timesheet_time / uom_ratio
        color = ""
        if allocated:
            number = f"{round(effective)} / {round(allocated)} {encode_uom.name}"
            success_rate = round(100 * effective / allocated)
            if success_rate > 100:
                number = self.env._(
                    "%(effective)s / %(allocated)s %(uom_name)s",
                    effective=round(effective),
                    allocated=round(allocated),
                    uom_name=encode_uom.name,
                )
                color = "text-danger"
            else:
                number = self.env._(
                    "%(effective)s / %(allocated)s %(uom_name)s (%(success_rate)s%%)",
                    effective=round(effective),
                    allocated=round(allocated),
                    uom_name=encode_uom.name,
                    success_rate=success_rate,
                )
                if success_rate >= 80:
                    color = "text-warning"
                else:
                    color = "text-success"
        else:
            number = self.env._(
                    "%(effective)s %(uom_name)s",
                    effective=round(effective),
                    uom_name=encode_uom.name,
                )

        buttons.append({
            "icon": f"clock-o {color}",
            "text": self.env._("Timesheets"),
            "number": number,
            "action_type": "object",
            "action": "action_project_timesheets",
            "show": True,
            "sequence": 2,
        })
        if allocated and success_rate > 100:
            buttons.append({
                "icon": f"warning {color}",
                "text": self.env._("Extra Time"),
                "number": self.env._(
                    "%(exceeding_hours)s %(uom_name)s (+%(exceeding_rate)s%%)",
                    exceeding_hours=round(effective - allocated),
                    uom_name=encode_uom.name,
                    exceeding_rate=round(100 * (effective - allocated) / allocated),
                ),
                "action_type": "object",
                "action": "action_project_timesheets",
                "show": True,
                "sequence": 3,
            })

        return buttons

    def action_view_tasks(self):
        # Using the timesheet filter hide context
        action = super().action_view_tasks()
        action['context']['allow_timesheets'] = self.allow_timesheets
        return action
