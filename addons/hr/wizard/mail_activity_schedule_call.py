# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models
from odoo.fields import Domain


class MailActivityScheduleCall(models.TransientModel):
    _inherit = 'mail.activity.schedule.call'

    employee_id = fields.Many2one('hr.employee', compute='_compute_employee_id', readonly=False)
    employee_id_domain = fields.Char(compute='_compute_employee_id_domain', export_string_translation=False)

    @api.depends('res_model_selection', 'employee_id_domain')
    def _compute_employee_id(self):
        for scheduler in self:
            if scheduler.employee_id or scheduler.res_model_selection != 'hr.employee':
                continue
            domain = literal_eval(scheduler.employee_id_domain)
            scheduler.employee_id = self.env.context.get('default_employee_id') or self._get_log_default_record(
                'hr.employee', domain,
            )

    @api.depends_context('log_contact_id', 'log_channel_partner_ids')
    def _compute_employee_id_domain(self):
        if not self.env.user.has_group('hr.group_hr_user'):
            # keep an always-empty domain: the user has no access to employees
            self.employee_id_domain = Domain.FALSE
            return
        if not self._is_logging_call():
            self.employee_id_domain = []
            return
        domain = [('company_id', 'in', self.env.companies.ids)]
        if contact := self._get_log_filter_contact():
            domain.append(('id', 'in', contact.employee_ids.ids))
        self.employee_id_domain = domain

    def _get_partner_from_target(self):
        if self.res_model == 'hr.employee':
            employee = self._get_applied_on_records()
            return employee.work_contact_id
        return super()._get_partner_from_target()

    def _get_res_model_fields(self):
        return {**super()._get_res_model_fields(), 'hr.employee': 'employee_id'}

    def _selection_res_model(self):
        res = super()._selection_res_model()
        if self.env.user.has_group('hr.group_hr_user'):
            res += [('hr.employee', self.env._("Employee"))]
        return res
