# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from lxml import etree
import re

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError, AccessError
from odoo.osv import expression

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    @api.model
    def default_get(self, field_list):
        result = super(AccountAnalyticLine, self).default_get(field_list)
        if 'encoding_uom_id' in field_list:
            result['encoding_uom_id'] = self.env.company.timesheet_encode_uom_id.id
        if not self.env.context.get('default_employee_id') and 'employee_id' in field_list and result.get('user_id'):
            result['employee_id'] = self.env['hr.employee'].search([('user_id', '=', result['user_id']), ('company_id', '=', result.get('company_id', self.env.company.id))], limit=1).id
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

    def _domain_task_id(self):
        if not self.user_has_groups('hr_timesheet.group_hr_timesheet_approver'):
            return ['|', ('privacy_visibility', '!=', 'followers'), ('message_partner_ids', 'in', [self.env.user.partner_id.id])]
        return []

    task_id = fields.Many2one(
        'project.task', 'Task', compute='_compute_task_id', store=True, readonly=False, index=True,
        domain="[('company_id', '=', company_id), ('project_id.allow_timesheets', '=', True), ('project_id', '=?', project_id)]")
    project_id = fields.Many2one(
        'project.project', 'Project', compute='_compute_project_id', store=True, readonly=False,
        domain=_domain_project_id)
    user_id = fields.Many2one(compute='_compute_user_id', store=True, readonly=False)
    employee_id = fields.Many2one('hr.employee', "Employee", domain=_domain_employee_id)
    department_id = fields.Many2one('hr.department', "Department", compute='_compute_department_id', store=True, compute_sudo=True)
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
        for line in self.filtered(lambda line: not line.project_id):
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
            line.user_id = line.employee_id.user_id if line.employee_id else line._default_user()

    @api.depends('employee_id')
    def _compute_department_id(self):
        for line in self:
            line.department_id = line.employee_id.department_id

    @api.model_create_multi
    def create(self, vals_list):
        default_user_id = self._default_user()
        user_ids = list(map(lambda x: x.get('user_id', default_user_id), filter(lambda x: not x.get('employee_id') and x.get('project_id'), vals_list)))

        for vals in vals_list:
            # when the name is not provide by the 'Add a line', we set a default one
            if vals.get('project_id') and not vals.get('name'):
                vals['name'] = '/'
            vals.update(self._timesheet_preprocess(vals))

        # Although this make a second loop on the vals, we need to wait the preprocess as it could change the company_id in the vals
        # TODO To be refactored in master
        company_ids_in_vals = list({vals['company_id'] for vals in vals_list if vals.get('company_id', False)})
        employees = self.env['hr.employee'].search([('user_id', 'in', user_ids), ('company_id', 'in', [self.env.company.id] + company_ids_in_vals)])
        user_map = defaultdict(dict)
        for employee in employees:
            user_map[employee.company_id.id][employee.user_id.id] = employee.id

        for vals in vals_list:
            # compute employee only for timesheet lines, makes no sense for other lines
            if not vals.get('employee_id') and vals.get('project_id'):
                vals['employee_id'] = user_map[vals.get('company_id', self.env.company.id)].get(vals.get('user_id', default_user_id), False)

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
        if 'name' in values and not values.get('name'):
            values['name'] = '/'
        result = super(AccountAnalyticLine, self).write(values)
        # applied only for timesheet
        self.filtered(lambda t: t.project_id)._timesheet_postprocess(values)
        return result

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """ Set the correct label for `unit_amount`, depending on company UoM """
        result = super(AccountAnalyticLine, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        result['arch'] = self._apply_timesheet_label(result['arch'], view_type=view_type)
        return result

    @api.model
    def _apply_timesheet_label(self, view_arch, view_type='form'):
        doc = etree.XML(view_arch)
        encoding_uom = self.env.company.timesheet_encode_uom_id
        # Here, we select only the unit_amount field having no string set to give priority to
        # custom inheretied view stored in database. Even if normally, no xpath can be done on
        # 'string' attribute.
        for node in doc.xpath("//field[@name='unit_amount'][@widget='timesheet_uom'][not(@string)]"):
            node.set('string', _('%s Spent') % (re.sub(r'[\(\)]', '', encoding_uom.name or '')))
        return etree.tostring(doc, encoding='unicode')

    @api.model
    def _apply_time_label(self, view_arch, related_model):
        doc = etree.XML(view_arch)
        Model = self.env[related_model]
        # Just fetch the name of the uom in `timesheet_encode_uom_id` of the current company
        encoding_uom_name = self.env.company.timesheet_encode_uom_id.with_context(prefetch_fields=False).sudo().name
        for node in doc.xpath("//field[@widget='timesheet_uom'][not(@string)] | //field[@widget='timesheet_uom_no_toggle'][not(@string)]"):
            name_with_uom = re.sub(_('Hours') + "|Hours", encoding_uom_name or '', Model._fields[node.get('name')]._description_string(self.env), flags=re.IGNORECASE)
            node.set('string', name_with_uom)

        return etree.tostring(doc, encoding='unicode')

    def _timesheet_get_portal_domain(self):
        if self.env.user.has_group('hr_timesheet.group_hr_timesheet_user'):
            # Then, he is internal user, and we take the domain for this current user
            return self.env['ir.rule']._compute_domain(self._name)
        return ['&',
                    '|',
                    ('task_id.project_id.message_partner_ids', 'child_of', [self.env.user.partner_id.commercial_partner_id.id]),
                    ('task_id.message_partner_ids', 'child_of', [self.env.user.partner_id.commercial_partner_id.id]),
                ('task_id.project_id.privacy_visibility', '=', 'portal')]

    def _timesheet_preprocess(self, vals):
        """ Deduce other field values from the one given.
            Overrride this to compute on the fly some field that can not be computed fields.
            :param values: dict values for `create`or `write`.
        """
        # task implies analytic account and tags
        if vals.get('task_id') and not vals.get('account_id'):
            task = self.env['project.task'].browse(vals.get('task_id'))
            task_analytic_account_id = task._get_task_analytic_account_id()
            vals['account_id'] = task_analytic_account_id.id
            vals['company_id'] = task_analytic_account_id.company_id.id or task.company_id.id
            if vals.get('tag_ids'):
                vals['tag_ids'] += [Command.link(tag_id.id) for tag_id in task.analytic_tag_ids]
            else:
                vals['tag_ids'] = [Command.set(task.analytic_tag_ids.ids)]
            if not task_analytic_account_id.active:
                raise UserError(_('You cannot add timesheets to a project or a task linked to an inactive analytic account.'))
        # project implies analytic account
        if vals.get('project_id') and not vals.get('account_id'):
            project = self.env['project.project'].browse(vals.get('project_id'))
            vals['account_id'] = project.analytic_account_id.id
            vals['company_id'] = project.analytic_account_id.company_id.id or project.company_id.id
            if not project.analytic_account_id.active:
                raise UserError(_('You cannot add timesheets to a project linked to an inactive analytic account.'))
        # employee implies user
        if vals.get('employee_id') and not vals.get('user_id'):
            employee = self.env['hr.employee'].browse(vals['employee_id'])
            vals['user_id'] = employee.user_id.id
        # force customer partner, from the task or the project
        if (vals.get('project_id') or vals.get('task_id')) and not vals.get('partner_id'):
            partner_id = False
            if vals.get('task_id'):
                partner_id = self.env['project.task'].browse(vals['task_id']).partner_id.id
            else:
                partner_id = self.env['project.project'].browse(vals['project_id']).partner_id.id
            if partner_id:
                vals['partner_id'] = partner_id
        # set timesheet UoM from the AA company (AA implies uom)
        if 'product_uom_id' not in vals and all(v in vals for v in ['account_id', 'project_id']):  # project_id required to check this is timesheet flow
            analytic_account = self.env['account.analytic.account'].sudo().browse(vals['account_id'])
            vals['product_uom_id'] = analytic_account.company_id.project_time_mode_id.id
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
                cost = timesheet._employee_timesheet_cost()
                amount = -timesheet.unit_amount * cost
                amount_converted = timesheet.employee_id.currency_id._convert(
                    amount, timesheet.account_id.currency_id, self.env.company, timesheet.date)
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

    def _employee_timesheet_cost(self):
        self.ensure_one()
        return self.employee_id.timesheet_cost or 0.0
