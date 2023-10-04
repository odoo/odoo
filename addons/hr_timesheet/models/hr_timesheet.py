# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from lxml import etree
import re

from odoo import api, Command, fields, models, _, _lt
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.osv import expression

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    @api.model
    def _get_favorite_project_id(self, employee_id=False):
        employee_id = employee_id or self.env.user.employee_id.id
        last_timesheet_ids = self.search([
            ('employee_id', '=', employee_id),
            ('project_id', '!=', False),
        ], limit=5)
        if len(last_timesheet_ids.project_id) == 1:
            return last_timesheet_ids.project_id.id
        return False

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
        if not self.user_has_groups('hr_timesheet.group_timesheet_manager'):
            return expression.AND([domain,
                ['|', ('privacy_visibility', '!=', 'followers'), ('message_partner_ids', 'in', [self.env.user.partner_id.id])]
            ])
        return domain

    def _domain_employee_id(self):
        if not self.user_has_groups('hr_timesheet.group_hr_timesheet_approver'):
            return [('user_id', '=', self.env.user.id)]
        return []

    task_id = fields.Many2one(
        'project.task', 'Task', index='btree_not_null',
        compute='_compute_task_id', store=True, readonly=False,
        domain="[('project_id.allow_timesheets', '=', True), ('project_id', '=?', project_id)]")
    ancestor_task_id = fields.Many2one('project.task', related='task_id.ancestor_id', store=True, index='btree_not_null')
    project_id = fields.Many2one(
        'project.project', 'Project', domain=_domain_project_id, index=True,
        compute='_compute_project_id', store=True, readonly=False)
    user_id = fields.Many2one(compute='_compute_user_id', store=True, readonly=False)
    employee_id = fields.Many2one('hr.employee', "Employee", domain=_domain_employee_id, context={'active_test': False},
        help="Define an 'hourly cost' on the employee to track the cost of their time.")
    job_title = fields.Char(related='employee_id.job_title')
    department_id = fields.Many2one('hr.department', "Department", compute='_compute_department_id', store=True, compute_sudo=True)
    manager_id = fields.Many2one('hr.employee', "Manager", related='employee_id.parent_id', store=True)
    encoding_uom_id = fields.Many2one('uom.uom', compute='_compute_encoding_uom_id')
    partner_id = fields.Many2one(compute='_compute_partner_id', store=True, readonly=False)

    def name_get(self):
        result = super().name_get()
        timesheets_read = self.env[self._name].search_read([('project_id', '!=', False), ('id', 'in', self.ids)], ['id', 'project_id', 'task_id'])
        if not timesheets_read:
            return result
        def _get_display_name(project_id, task_id):
            """ Get the display name of the timesheet based on the project and task
                :param project_id: tuple containing the id and the display name of the project
                :param task_id: tuple containing the id and the display name of the task if a task exists in the timesheet
                              otherwise False.
                :returns: the display name of the timesheet
            """
            if task_id:
                return '%s - %s' % (project_id[1], task_id[1])
            return project_id[1]
        timesheet_dict = {res['id']: _get_display_name(res['project_id'], res['task_id']) for res in timesheets_read}
        return list({**dict(result), **timesheet_dict}.items())

    def _compute_encoding_uom_id(self):
        for analytic_line in self:
            analytic_line.encoding_uom_id = analytic_line.company_id.timesheet_encode_uom_id

    @api.depends('task_id.partner_id', 'project_id.partner_id')
    def _compute_partner_id(self):
        for timesheet in self:
            if timesheet.project_id:
                timesheet.partner_id = timesheet.task_id.partner_id or timesheet.project_id.partner_id

    @api.depends('task_id', 'task_id.project_id')
    def _compute_project_id(self):
        for line in self:
            if not line.task_id.project_id or line.project_id == line.task_id.project_id:
                continue
            line.project_id = line.task_id.project_id

    @api.depends('project_id')
    def _compute_task_id(self):
        for line in self.filtered(lambda line: not line.project_id):
            line.task_id = False

    @api.onchange('project_id')
    def _onchange_project_id(self):
        # TODO KBA in master - check to do it "properly", currently:
        # This onchange is used to reset the task_id when the project changes.
        # Doing it in the compute will remove the task_id when the project of a task changes.
        if self.project_id != self.task_id.project_id:
            self.task_id = False

    @api.depends('employee_id')
    def _compute_user_id(self):
        for line in self:
            line.user_id = line.employee_id.user_id if line.employee_id else self._default_user()

    @api.depends('employee_id')
    def _compute_department_id(self):
        for line in self:
            line.department_id = line.employee_id.department_id

    @api.model_create_multi
    def create(self, vals_list):
        # Before creating a timesheet, we need to put a valid employee_id in the vals
        default_user_id = self._default_user()
        user_ids = []
        employee_ids = []
        # 1/ Collect the user_ids and employee_ids from each timesheet vals
        for vals in vals_list:
            vals.update(self._timesheet_preprocess(vals))
            if not vals.get('project_id'):
                continue
            if not vals.get('name'):
                vals['name'] = '/'
            employee_id = vals.get('employee_id')
            user_id = vals.get('user_id', default_user_id)
            if employee_id and employee_id not in employee_ids:
                employee_ids.append(employee_id)
            elif user_id not in user_ids:
                user_ids.append(user_id)

        # 2/ Search all employees related to user_ids and employee_ids, in the selected companies
        employees = self.env['hr.employee'].sudo().search([
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
        error_msg = _lt('Timesheets must be created with an active employee in the selected companies.')
        for vals in vals_list:
            if not vals.get('project_id'):
                continue
            employee_in_id = vals.get('employee_id')
            if employee_in_id:
                if employee_in_id in valid_employee_per_id:
                    vals['user_id'] = valid_employee_per_id[employee_in_id].sudo().user_id.id   # (A) OK
                    continue
                else:
                    raise ValidationError(error_msg)                                      # (C) KO
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
            else:  # ...and raise an error if they fail
                raise ValidationError(error_msg)

        # 5/ Finally, create the timesheets
        lines = super(AccountAnalyticLine, self).create(vals_list)
        for line, values in zip(lines, vals_list):
            if line.project_id:  # applied only for timesheet
                line._timesheet_postprocess(values)
        return lines

    def write(self, values):
        # If it's a basic user then check if the timesheet is his own.
        if not (self.user_has_groups('hr_timesheet.group_hr_timesheet_approver') or self.env.su) and any(self.env.user.id != analytic_line.user_id.id for analytic_line in self):
            raise AccessError(_("You cannot access timesheets that are not yours."))

        values = self._timesheet_preprocess(values)
        if values.get('employee_id'):
            employee = self.env['hr.employee'].browse(values['employee_id'])
            if not employee.active:
                raise UserError(_('You cannot set an archived employee to the existing timesheets.'))
        if 'name' in values and not values.get('name'):
            values['name'] = '/'
        result = super(AccountAnalyticLine, self).write(values)
        # applied only for timesheet
        self.filtered(lambda t: t.project_id)._timesheet_postprocess(values)
        return result

    @api.model
    def _get_view_cache_key(self, view_id=None, view_type='form', **options):
        """The override of _get_view changing the time field labels according to the company timesheet encoding UOM
        makes the view cache dependent on the company timesheet encoding uom"""
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + (self.env.company.timesheet_encode_uom_id,)

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        """ Set the correct label for `unit_amount`, depending on company UoM """
        arch, view = super()._get_view(view_id, view_type, **options)
        arch = self.sudo()._apply_timesheet_label(arch, view_type=view_type)
        return arch, view

    @api.model
    def _apply_timesheet_label(self, view_node, view_type='form'):
        doc = view_node
        encoding_uom = self.env.company.timesheet_encode_uom_id
        # Here, we select only the unit_amount field having no string set to give priority to
        # custom inheretied view stored in database. Even if normally, no xpath can be done on
        # 'string' attribute.
        for node in doc.xpath("//field[@name='unit_amount'][@widget='timesheet_uom'][not(@string)]"):
            node.set('string', _('%s Spent') % (re.sub(r'[\(\)]', '', encoding_uom.name or '')))
        return doc

    @api.model
    def _apply_time_label(self, view_node, related_model):
        doc = view_node
        Model = self.env[related_model]
        # Just fetch the name of the uom in `timesheet_encode_uom_id` of the current company
        encoding_uom_name = self.env.company.timesheet_encode_uom_id.with_context(prefetch_fields=False).sudo().name
        for node in doc.xpath("//field[@widget='timesheet_uom'][not(@string)] | //field[@widget='timesheet_uom_no_toggle'][not(@string)]"):
            name_with_uom = re.sub(_('Hours') + "|Hours", encoding_uom_name or '', Model._fields[node.get('name')]._description_string(self.env), flags=re.IGNORECASE)
            node.set('string', name_with_uom)

        return doc

    def _timesheet_get_portal_domain(self):
        if self.env.user.has_group('hr_timesheet.group_hr_timesheet_user'):
            # Then, he is internal user, and we take the domain for this current user
            return self.env['ir.rule']._compute_domain(self._name)
        return [
            '|',
                '&',
                    '|',
                        ('task_id.project_id.message_partner_ids', 'child_of', [self.env.user.partner_id.commercial_partner_id.id]),
                        ('task_id.message_partner_ids', 'child_of', [self.env.user.partner_id.commercial_partner_id.id]),
                    ('task_id.project_id.privacy_visibility', '=', 'portal'),
                '&',
                    ('task_id', '=', False),
                    '&',
                        ('project_id.message_partner_ids', 'child_of', [self.env.user.partner_id.commercial_partner_id.id]),
                        ('project_id.privacy_visibility', '=', 'portal')
        ]

    def _timesheet_preprocess(self, vals):
        """ Deduce other field values from the one given.
            Overrride this to compute on the fly some field that can not be computed fields.
            :param values: dict values for `create`or `write`.
        """
        project = self.env['project.project'].browse(vals.get('project_id', False))
        task = self.env['project.task'].browse(vals.get('task_id', False))
        # task implies project
        if task and not project:
            project = task.project_id
            if not project:
                raise ValidationError(_('You cannot create a timesheet on a private task.'))
            vals['project_id'] = project.id
        # task implies analytic account and tags
        if task and not vals.get('account_id'):
            task_analytic_account_id = task._get_task_analytic_account_id()
            vals['account_id'] = task_analytic_account_id.id
            vals['company_id'] = task_analytic_account_id.company_id.id or task.company_id.id
            if not task_analytic_account_id.active:
                raise UserError(_('You cannot add timesheets to a project or a task linked to an inactive analytic account.'))
        # project implies analytic account
        elif project and not vals.get('account_id'):
            vals['account_id'] = project.analytic_account_id.id
            vals['company_id'] = project.analytic_account_id.company_id.id or project.company_id.id
            if not project.analytic_account_id.active:
                raise UserError(_('You cannot add timesheets to a project linked to an inactive analytic account.'))
        # force customer partner, from the task or the project
        if project and not vals.get('partner_id'):
            partner_id = task.partner_id.id if task else project.partner_id.id
            if partner_id:
                vals['partner_id'] = partner_id
        # set timesheet UoM from the AA company (AA implies uom)
        if not vals.get('product_uom_id') and all(v in vals for v in ['account_id', 'project_id']):  # project_id required to check this is timesheet flow
            analytic_account = self.env['account.analytic.account'].sudo().browse(vals['account_id'])
            uom_id = analytic_account.company_id.project_time_mode_id.id
            if not uom_id:
                company_id = vals.get('company_id', False)
                if not company_id:
                    project = self.env['project.project'].browse(vals.get('project_id'))
                    company_id = project.analytic_account_id.company_id.id or project.company_id.id
                uom_id = self.env['res.company'].browse(company_id).project_time_mode_id.id
            vals['product_uom_id'] = uom_id
        return vals

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
