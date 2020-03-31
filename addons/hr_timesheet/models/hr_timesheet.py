# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError
from odoo.osv import expression

class AccountAnalyticLine(models.Model):
    _name = 'account.analytic.line'
    _inherit = ['account.analytic.line', 'timer.mixin']

    @api.model
    def default_get(self, field_list):
        result = super(AccountAnalyticLine, self).default_get(field_list)
        if 'encoding_uom_id' in field_list:
            result['encoding_uom_id'] = self.env.company.timesheet_encode_uom_id.id
        if not self.env.context.get('default_employee_id') and 'employee_id' in field_list and result.get('user_id'):
            result['employee_id'] = self.env['hr.employee'].search([('user_id', '=', result['user_id'])], limit=1).id
        return result

    def _domain_project_id(self):
        domain = [('allow_timesheets', '=', True)]
        if not self.user_has_groups('hr_timesheet.group_timesheet_manager'):
            return expression.AND([domain,
                ['|', ('privacy_visibility', '!=', 'followers'), ('allowed_internal_user_ids', 'in', self.env.user.ids)]
            ])
        return domain

    def _domain_employee_id(self):
        if not self.user_has_groups('hr_timesheet.group_hr_timesheet_approver'):
            return [('user_id', '=', self.env.user.id)]
        return []

    def _domain_task_id(self):
        if not self.user_has_groups('hr_timesheet.group_hr_timesheet_approver'):
            return ['|', ('privacy_visibility', '!=', 'followers'), ('allowed_user_ids', 'in', self.env.user.ids)]
        return []

    task_id = fields.Many2one(
        'project.task', 'Task', index=True,
        domain="[('company_id', '=', company_id), ('project_id.allow_timesheets', '=', True), ('project_id', '=?', project_id)]"
    )
    project_id = fields.Many2one('project.project', 'Project', domain=_domain_project_id)

    employee_id = fields.Many2one('hr.employee', "Employee", check_company=True, domain=_domain_employee_id)
    department_id = fields.Many2one('hr.department', "Department", compute='_compute_department_id', store=True, compute_sudo=True)
    encoding_uom_id = fields.Many2one('uom.uom', compute='_compute_encoding_uom_id')
    display_timer = fields.Boolean(
        compute='_compute_display_timer',
        help="Technical field used to display the timer if the encoding unit is 'Hours'.")

    def _compute_encoding_uom_id(self):
        for analytic_line in self:
            analytic_line.encoding_uom_id = self.env.company.timesheet_encode_uom_id

    @api.onchange('project_id')
    def onchange_project_id(self):
        if self.project_id and self.project_id != self.task_id.project_id:
            # reset task when changing project
            self.task_id = False

    @api.onchange('task_id')
    def _onchange_task_id(self):
        if not self.project_id:
            self.project_id = self.task_id.project_id

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.user_id = self.employee_id.user_id
        else:
            self.user_id = self._default_user()

    @api.depends('employee_id')
    def _compute_department_id(self):
        for line in self:
            line.department_id = line.employee_id.department_id

    @api.model_create_multi
    def create(self, vals_list):
        default_user_id = self._default_user()
        user_ids = list(map(lambda x: x.get('user_id', default_user_id), filter(lambda x: not x.get('employee_id') and x.get('project_id'), vals_list)))
        employees = self.env['hr.employee'].search([('user_id', 'in', user_ids)])
        user_map = {employee.user_id.id: employee.id for employee in employees}

        for vals in vals_list:
            # when the name is not provide by the 'Add a line', we set a default one
            if vals.get('project_id') and not vals.get('name'):
                vals['name'] = _('/')
            # compute employee only for timesheet lines, makes no sense for other lines
            if not vals.get('employee_id') and vals.get('project_id'):
                vals['employee_id'] = user_map.get(vals.get('user_id') or default_user_id)
            vals.update(self._timesheet_preprocess(vals))

        lines = super(AccountAnalyticLine, self).create(vals_list)
        for line, values in zip(lines, vals_list):
            if line.project_id:  # applied only for timesheet
                line._timesheet_postprocess(values)
        return lines

    def write(self, values):
        # If it's a basic user then check if the timesheet is his own.
        if not self.user_has_groups('hr_timesheet.group_hr_timesheet_approver') and any(self.env.user.id != analytic_line.user_id.id for analytic_line in self):
            raise AccessError(_("You cannot access timesheets that are not yours."))

        values = self._timesheet_preprocess(values)
        result = super(AccountAnalyticLine, self).write(values)
        # applied only for timesheet
        self.filtered(lambda t: t.project_id)._timesheet_postprocess(values)
        return result

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """ Set the correct label for `unit_amount`, depending on company UoM """
        result = super(AccountAnalyticLine, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        result['arch'] = self._apply_timesheet_label(result['arch'])
        return result

    @api.model
    def _apply_timesheet_label(self, view_arch):
        doc = etree.XML(view_arch)
        encoding_uom = self.env.company.timesheet_encode_uom_id
        # Here, we select only the unit_amount field having no string set to give priority to
        # custom inheretied view stored in database. Even if normally, no xpath can be done on
        # 'string' attribute.
        for node in doc.xpath("//field[@name='unit_amount'][@widget='timesheet_uom'][not(@string)]"):
            node.set('string', _('Duration (%s)') % (re.sub(r'[\(\)]', '', encoding_uom.name or '')))
        return etree.tostring(doc, encoding='unicode')

    def _timesheet_get_portal_domain(self):
        return ['|', '&',
                ('task_id.project_id.privacy_visibility', '=', 'portal'),
                ('task_id.project_id.message_partner_ids', 'child_of', [self.env.user.partner_id.commercial_partner_id.id]),
                '&',
                ('task_id.project_id.privacy_visibility', '=', 'portal'),
                ('task_id.message_partner_ids', 'child_of', [self.env.user.partner_id.commercial_partner_id.id])]

    def _timesheet_preprocess(self, vals):
        """ Deduce other field values from the one given.
            Overrride this to compute on the fly some field that can not be computed fields.
            :param values: dict values for `create`or `write`.
        """
        # project implies analytic account
        if vals.get('project_id') and not vals.get('account_id'):
            project = self.env['project.project'].browse(vals.get('project_id'))
            vals['account_id'] = project.analytic_account_id.id
            vals['company_id'] = project.analytic_account_id.company_id.id
            if not project.analytic_account_id.active:
                raise UserError(_('The project you are timesheeting on is not linked to an active analytic account. Set one on the project configuration.'))
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
        if 'product_uom_id' not in vals and all([v in vals for v in ['account_id', 'project_id']]):  # project_id required to check this is timesheet flow
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
        if any([field_name in values for field_name in ['unit_amount', 'employee_id', 'account_id']]):
            for timesheet in sudo_self:
                cost = timesheet.employee_id.timesheet_cost or 0.0
                amount = -timesheet.unit_amount * cost
                amount_converted = timesheet.employee_id.currency_id._convert(
                    amount, timesheet.account_id.currency_id, self.env.company, timesheet.date)
                result[timesheet.id].update({
                    'amount': amount_converted,
                })
        return result

    def _compute_display_timer(self):
        uom_hour = self.env.ref('uom.product_uom_hour')
        for analytic_line in self:
            analytic_line.display_timer = analytic_line.encoding_uom_id == uom_hour

    def action_timer_start(self):
        """ Start a timer if it isn't already started and the
        timesheets allow to track time
        """
        if not self.user_timer_id.timer_start and self.display_timer:
            super().action_timer_start()

    def action_timer_stop(self):
        """ Stop the current timer
        """
        if self.user_timer_id.timer_start and self.display_timer:
            minutes_spent = super().action_timer_stop()
            self._add_timesheet_time(minutes_spent)

    def _add_timesheet_time(self, minutes_spent):
        if self.unit_amount == 0 and minutes_spent < 1:
            # Check if unit_amount equals 0 and minutes_spent is less than 1 minute,
            # if yes, then remove the timesheet
            self.unlink()
        else:
            if minutes_spent < 1:
                amount = self.unit_amount
            else:
                minimum_duration = int(self.env['ir.config_parameter'].sudo().get_param('hr_timesheet.timesheet_min_duration', 0))
                rounding = int(self.env['ir.config_parameter'].sudo().get_param('hr_timesheet.timesheet_rounding', 0))
                minutes_spent = self._timer_rounding(minutes_spent, minimum_duration, rounding)
                amount = self.unit_amount + minutes_spent * 60 / 3600
            self.write({'unit_amount': amount})

    def _action_interrupt_user_timers(self):
        self.action_timer_stop()