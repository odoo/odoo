# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from statistics import mode
import re

from odoo import api, fields, models
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.osv import expression
from odoo.tools import format_list
from odoo.tools.translate import _


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def _get_favorite_project_id_domain(self, employee_id=False):
        employee_id = employee_id or self.env.user.employee_id.id
        return [
            ('employee_id', '=', employee_id),
            ('project_id', '!=', False),
            ('project_id.active', '=', True),
        ]

    @api.model
    def _get_favorite_project_id(self, employee_id=False):
        last_timesheets = self.search_fetch(
            self._get_favorite_project_id_domain(employee_id), ['project_id'], limit=5
        )
        if not last_timesheets:
            internal_project = self.env.company.internal_project_id
            return internal_project.active and internal_project.id
        return mode([t.project_id.id for t in last_timesheets])

    @api.model
    def default_get(self, field_list):
        result = super(AccountAnalyticLine, self).default_get(field_list)
        if not self.env.context.get('default_employee_id') and 'employee_id' in field_list and result.get('user_id'):
            result['employee_id'] = self.env['hr.employee'].search([('user_id', '=', result['user_id']), ('company_id', '=', result.get('company_id', self.env.company.id))], limit=1).id
        if not self._context.get('default_project_id') and self._context.get('is_timesheet'):
            employee_id = result.get('employee_id', self.env.context.get('default_employee_id', False))
            favorite_project_id = self._get_favorite_project_id(employee_id)
            if favorite_project_id:
                result['project_id'] = favorite_project_id
        return result

    def _domain_project_id(self):
        domain = [('allow_timesheets', '=', True)]
        if not self.env.user.has_group('hr_timesheet.group_timesheet_manager'):
            return expression.AND([domain,
                ['|', ('privacy_visibility', '!=', 'followers'), ('message_partner_ids', 'in', [self.env.user.partner_id.id])]
            ])
        return domain

    def _domain_employee_id(self):
        domain = [('company_id', 'in', self._context.get('allowed_company_ids'))]
        if not self.env.user.has_group('hr_timesheet.group_hr_timesheet_approver'):
            domain = expression.AND([domain, [('user_id', '=', self.env.user.id)]])
        return domain

    task_id = fields.Many2one(
        'project.task', 'Task', index='btree_not_null',
        compute='_compute_task_id', store=True, readonly=False,
        domain="[('allow_timesheets', '=', True), ('project_id', '=?', project_id)]")
    parent_task_id = fields.Many2one('project.task', related='task_id.parent_id', store=True)
    project_id = fields.Many2one(
        'project.project', 'Project', domain=_domain_project_id, index=True,
        compute='_compute_project_id', store=True, readonly=False)
    user_id = fields.Many2one(compute='_compute_user_id', store=True, readonly=False)
    employee_id = fields.Many2one('hr.employee', "Employee", domain=_domain_employee_id, context={'active_test': False},
        index=True, help="Define an 'hourly cost' on the employee to track the cost of their time.")
    job_title = fields.Char(related='employee_id.job_title', export_string_translation=False)
    department_id = fields.Many2one('hr.department', "Department", compute='_compute_department_id', store=True, compute_sudo=True)
    manager_id = fields.Many2one('hr.employee', "Manager", related='employee_id.parent_id', store=True)
    encoding_uom_id = fields.Many2one('uom.uom', compute='_compute_encoding_uom_id', export_string_translation=False)
    partner_id = fields.Many2one(compute='_compute_partner_id', store=True, readonly=False)
    readonly_timesheet = fields.Boolean(compute="_compute_readonly_timesheet", compute_sudo=True, export_string_translation=False)
    milestone_id = fields.Many2one('project.milestone', related='task_id.milestone_id')
    message_partner_ids = fields.Many2many('res.partner', compute='_compute_message_partner_ids', search='_search_message_partner_ids')

    def _search_message_partner_ids(self, operator, value):
        followed_ids_by_model = dict(self.env['mail.followers']._read_group([
            ('partner_id', operator, value),
            ('res_model', 'in', ('project.project', 'project.task')),
        ], ['res_model'], ['res_id:array_agg']))
        if not followed_ids_by_model:
            return expression.FALSE_DOMAIN
        domains = []
        if project_ids := followed_ids_by_model.get('project.project'):
            domains.append([('project_id', 'in', project_ids)])
        if task_ids := followed_ids_by_model.get('project.task'):
            domains.append([('task_id', 'in', task_ids)])
        domain = expression.OR(domains)
        return domain

    @api.depends('project_id.message_partner_ids', 'task_id.message_partner_ids')
    def _compute_message_partner_ids(self):
        for line in self:
            line.message_partner_ids = line.task_id.message_partner_ids | line.project_id.message_partner_ids

    @api.depends('project_id', 'task_id')
    def _compute_display_name(self):
        analytic_line_with_project = self.filtered('project_id')
        super(AccountAnalyticLine, self - analytic_line_with_project)._compute_display_name()
        for analytic_line in analytic_line_with_project:
            if analytic_line.task_id:
                analytic_line.display_name = f"{analytic_line.project_id.display_name} - {analytic_line.task_id.display_name}"
            else:
                analytic_line.display_name = analytic_line.project_id.display_name

    def _is_readonly(self):
        self.ensure_one()
        # is overridden in other timesheet related modules
        return False

    def _compute_readonly_timesheet(self):
        # Since the mrp_module gives write access to portal user on timesheet, we check that the user is an internal one before giving the write access.
        # It is not supposed to be needed, since portal user are not supposed to have access to the views using this field, but better be safe than sorry
        if not self.env.user.has_group('base.group_user'):
            self.readonly_timesheet = True
        else:
            readonly_timesheets = self.filtered(lambda timesheet: timesheet._is_readonly())
            readonly_timesheets.readonly_timesheet = True
            (self - readonly_timesheets).readonly_timesheet = False

    def _compute_encoding_uom_id(self):
        for analytic_line in self:
            analytic_line.encoding_uom_id = analytic_line.company_id.timesheet_encode_uom_id

    @api.depends('task_id.partner_id', 'project_id.partner_id')
    def _compute_partner_id(self):
        for timesheet in self:
            if timesheet.project_id:
                timesheet.partner_id = timesheet.task_id.partner_id or timesheet.project_id.partner_id

    @api.depends('task_id.project_id')
    def _compute_project_id(self):
        for line in self:
            if not line.task_id.project_id or line.project_id == line.task_id.project_id:
                continue
            line.project_id = line.task_id.project_id

    @api.depends('project_id')
    def _compute_task_id(self):
        self.filtered(lambda t: not t.project_id).task_id = False

    @api.onchange('project_id')
    def _onchange_project_id(self):
        # TODO KBA in master - check to do it "properly", currently:
        # This onchange is used to reset the task_id when the project changes.
        # Doing it in the compute will remove the task_id when the project of a task changes.
        if self.project_id != self.task_id.project_id:
            self.task_id = False

    @api.depends('employee_id.user_id')
    def _compute_user_id(self):
        for line in self:
            line.user_id = line.employee_id.user_id if line.employee_id else self._default_user()

    @api.depends('employee_id')
    def _compute_department_id(self):
        for line in self:
            line.department_id = line.employee_id.department_id

    def _check_can_write(self, values):
        # If it's a basic user then check if the timesheet is his own.
        if (
            not (self.env.user.has_group('hr_timesheet.group_hr_timesheet_approver') or self.env.su)
            and any(analytic_line.user_id != self.env.user for analytic_line in self)
        ):
            raise AccessError(_("You cannot access timesheets that are not yours."))

    def _check_can_create(self):
        # override in other modules to check current user has create access
        pass

    @api.model_create_multi
    def create(self, vals_list):
        # Before creating a timesheet, we need to put a valid employee_id in the vals
        default_user_id = self._default_user()
        user_ids = []
        employee_ids = []
        # 1/ Collect the user_ids and employee_ids from each timesheet vals
        for vals in vals_list:
            task = self.env['project.task'].sudo().browse(vals.get('task_id'))
            project = self.env['project.project'].sudo().browse(vals.get('project_id'))
            if not (task or project):
                # It is not a timesheet
                continue
            elif task:
                if not task.project_id:
                    raise ValidationError(_('Timesheets cannot be created on a private task.'))
                if not project:
                    vals['project_id'] = task.project_id.id

            company = task.company_id or project.company_id or self.env['res.company'].browse(vals.get('company_id'))
            vals['company_id'] = company.id
            vals.update(self._timesheet_preprocess_get_accounts(vals))

            if not vals.get('product_uom_id'):
                vals['product_uom_id'] = company.project_time_mode_id.id

            if not vals.get('name'):
                vals['name'] = '/'
            employee_id = vals.get('employee_id', self._context.get('default_employee_id', False))
            if employee_id and employee_id not in employee_ids:
                employee_ids.append(employee_id)
            else:
                user_id = vals.get('user_id', default_user_id)
                if user_id not in user_ids:
                    user_ids.append(user_id)

        # 2/ Search all employees related to user_ids and employee_ids, in the selected companies
        HrEmployee_sudo = self.env['hr.employee'].sudo()
        employees = HrEmployee_sudo.search([
            '&', '|', ('user_id', 'in', user_ids), ('id', 'in', employee_ids), ('company_id', 'in', self.env.companies.ids)
        ])

        #                 ┌───── in search results = active/in companies ────────> was found with... ─── employee_id ───> (A) There is nothing to do, we will use this employee_id
        # 3/ Each employee                                                                          └──── user_id ──────> (B)** We'll need to select the right employee for this user
        #                 └─ not in search results = archived/not in companies ──> (C) We raise an error as we can't create a timesheet for an archived employee
        # ** We can rely on the user to get the employee_id if
        #    he has an active employee in the company of the timesheet
        #    or he has only one active employee for all selected companies
        valid_employee_per_id = {}
        employee_id_per_company_per_user = defaultdict(dict)
        for employee in employees:
            if employee.id in employee_ids:
                valid_employee_per_id[employee.id] = employee
            else:
                employee_id_per_company_per_user[employee.user_id.id][employee.company_id.id] = employee.id

        # 4/ Put valid employee_id in each vals
        error_msg = _('Timesheets must be created with an active employee in the selected companies.')
        for vals in vals_list:
            if not vals.get('project_id'):
                continue
            employee_in_id = vals.get('employee_id', self._context.get('default_employee_id', False))
            if employee_in_id:
                company = False
                if not vals.get('company_id'):
                    company = HrEmployee_sudo.browse(employee_in_id).company_id
                    vals['company_id'] = company.id
                if not vals.get('product_uom_id'):
                    vals['product_uom_id'] = company.project_time_mode_id.id if company else self.env['res.company'].browse(vals.get('company_id', self.env.company.id)).project_time_mode_id.id
                if employee_in_id in valid_employee_per_id:
                    vals['user_id'] = valid_employee_per_id[employee_in_id].sudo().user_id.id   # (A) OK
                    continue
                else:
                    raise ValidationError(error_msg)                                            # (C) KO
            else:
                user_id = vals.get('user_id', default_user_id)                                  # (B)...

            # ...Look for an employee, with ** conditions
            employee_per_company = employee_id_per_company_per_user.get(user_id)
            employee_out_id = False
            if employee_per_company:
                company_id = list(employee_per_company)[0] if len(employee_per_company) == 1\
                        else vals.get('company_id', self.env.company.id)
                employee_out_id = employee_per_company.get(company_id, False)

            if employee_out_id:
                vals['employee_id'] = employee_out_id
                vals['user_id'] = user_id
                company = False
                if not vals.get('company_id'):
                    company = HrEmployee_sudo.browse(employee_out_id).company_id
                    vals['company_id'] = company.id
                if not vals.get('product_uom_id'):
                    vals['product_uom_id'] = company.project_time_mode_id.id if company else self.env['res.company'].browse(vals.get('company_id', self.env.company.id)).project_time_mode_id.id
            else:  # ...and raise an error if they fail
                raise ValidationError(error_msg)

        # 5/ Finally, create the timesheets
        lines = super(AccountAnalyticLine, self).create(vals_list)
        lines._check_can_create()
        for line, values in zip(lines, vals_list):
            if line.project_id:  # applied only for timesheet
                line._timesheet_postprocess(values)
        return lines

    def write(self, values):
        self._check_can_write(values)

        task = self.env['project.task'].sudo().browse(values.get('task_id'))
        project = self.env['project.project'].sudo().browse(values.get('project_id'))
        if task and not task.project_id:
            raise ValidationError(_('Timesheets cannot be created on a private task.'))
        if project or task:
            values['company_id'] = task.company_id.id or project.company_id.id
        values.update(self._timesheet_preprocess_get_accounts(values))

        if values.get('employee_id'):
            employee = self.env['hr.employee'].browse(values['employee_id'])
            if not employee.active:
                raise UserError(_('You cannot set an archived employee on existing timesheets.'))
        if 'name' in values and not values.get('name'):
            values['name'] = '/'
        if 'company_id' in values and not values.get('company_id'):
            del values['company_id']
        result = super(AccountAnalyticLine, self).write(values)
        # applied only for timesheet
        self.filtered(lambda t: t.project_id)._timesheet_postprocess(values)
        return result

    @api.model
    def get_views(self, views, options=None):
        res = super().get_views(views, options)
        if options and options.get('toolbar'):
            wip_report_id = None

            def get_wip_report_id():
                return self.env['ir.model.data']._xmlid_to_res_id("mrp_account.wip_report", raise_if_not_found=False)

            for view_data in res['views'].values():
                print_data_list = view_data.get('toolbar', {}).get('print')
                if print_data_list:
                    if wip_report_id is None and re.search(r'widget="timesheet_uom(\w)*"', view_data['arch']):
                        wip_report_id = get_wip_report_id()
                    if wip_report_id:
                        view_data['toolbar']['print'] = [print_data for print_data in print_data_list if print_data['id'] != wip_report_id]
        return res

    def _timesheet_get_portal_domain(self):
        if self.env.user.has_group('hr_timesheet.group_hr_timesheet_user'):
            # Then, he is internal user, and we take the domain for this current user
            return self.env['ir.rule']._compute_domain(self._name)
        return [
            ('message_partner_ids', 'child_of', [self.env.user.partner_id.commercial_partner_id.id]),
            ('project_id.privacy_visibility', '=', 'portal'),
        ]

    def _timesheet_preprocess_get_accounts(self, vals):
        project = self.env['project.project'].sudo().browse(vals.get('project_id'))
        if not project:
            return {}
        company = self.env['res.company'].browse(vals.get('company_id'))
        mandatory_plans = [plan for plan in self._get_mandatory_plans(company, business_domain='timesheet') if plan['column_name'] != 'account_id']
        missing_plan_names = [plan['name'] for plan in mandatory_plans if not project[plan['column_name']]]
        if missing_plan_names:
            raise ValidationError(_(
                "'%(missing_plan_names)s' analytic plan(s) required on the project '%(project_name)s' linked to the timesheet.",
                missing_plan_names=format_list(self.env, missing_plan_names),
                project_name=project.name,
            ))
        return {
            fname: project[fname].id
            for fname in self._get_plan_fnames()
        }

    def _timesheet_postprocess(self, values):
        """ Hook to update record one by one according to the values of a `write` or a `create`. """
        sudo_self = self.sudo()  # this creates only one env for all operation that required sudo() in `_timesheet_postprocess_values`override
        values_to_write = self._timesheet_postprocess_values(values)
        for timesheet in sudo_self:
            if values_to_write[timesheet.id]:
                timesheet.write(values_to_write[timesheet.id])
        return values

    def _timesheet_postprocess_values(self, values):
        """ Get the addionnal values to write on record
            :param dict values: values for the model's fields, as a dictionary::
                {'field_name': field_value, ...}
            :return: a dictionary mapping each record id to its corresponding
                dictionary values to write (may be empty).
        """
        result = {id_: {} for id_ in self.ids}
        sudo_self = self.sudo()  # this creates only one env for all operation that required sudo()
        # (re)compute the amount (depending on unit_amount, employee_id for the cost, and account_id for currency)
        if any(field_name in values for field_name in ['unit_amount', 'employee_id', 'account_id']):
            for timesheet in sudo_self:
                if not timesheet.account_id.active:
                    project_plan, _other_plans = self.env['account.analytic.plan']._get_all_plans()
                    raise ValidationError(_(
                        "Timesheets must be created with at least an active analytic account defined in the plan '%(plan_name)s'.",
                        plan_name=project_plan.name
                    ))
                accounts = timesheet._get_analytic_accounts()
                companies = timesheet.company_id | accounts.company_id | timesheet.task_id.company_id | timesheet.project_id.company_id
                if len(companies) > 1:
                    raise ValidationError(_('The project, the task and the analytic accounts of the timesheet must belong to the same company.'))

                cost = timesheet._hourly_cost()
                amount = -timesheet.unit_amount * cost
                amount_converted = timesheet.employee_id.currency_id._convert(
                    amount, timesheet.account_id.currency_id or timesheet.currency_id, self.env.company, timesheet.date)
                result[timesheet.id].update({
                    'amount': amount_converted,
                })
        return result

    def _is_timesheet_encode_uom_day(self):
        company_uom = self.env.company.timesheet_encode_uom_id
        return company_uom == self.env.ref('uom.product_uom_day')

    def _is_updatable_timesheet(self):
        return True

    @api.model
    def _convert_hours_to_days(self, time):
        uom_hour = self.env.ref('uom.product_uom_hour')
        uom_day = self.env.ref('uom.product_uom_day')
        return round(uom_hour._compute_quantity(time, uom_day, raise_if_failure=False), 2)

    def _get_timesheet_time_day(self):
        return self._convert_hours_to_days(self.unit_amount)

    def _hourly_cost(self):
        self.ensure_one()
        return self.employee_id.hourly_cost or 0.0

    def _get_report_base_filename(self):
        task_ids = self.task_id
        if len(task_ids) == 1:
            return _('Timesheets - %s', task_ids.name)
        return _('Timesheets')

    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    @api.model
    def _ensure_uom_hours(self):
        uom_hours = self.env.ref('uom.product_uom_hour', raise_if_not_found=False)
        if not uom_hours:
            uom_hours = self.env['uom.uom'].create({
                'name': "Hours",
                'category_id': self.env.ref('uom.uom_categ_wtime').id,
                'factor': 8,
                'uom_type': "smaller",
            })
            self.env['ir.model.data'].create({
                'name': 'product_uom_hour',
                'model': 'uom.uom',
                'module': 'uom',
                'res_id': uom_hours.id,
                'noupdate': True,
            })
