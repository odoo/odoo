# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta

from openerp import api, fields, models, _
from openerp.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    appraisal_date = fields.Date(string='Next Appraisal Date', help="The date of the next appraisal is computed by the appraisal plan's dates (first appraisal + periodicity).")
    appraisal_by_manager = fields.Boolean(string='Managers')
    appraisal_manager_ids = fields.Many2many('hr.employee', 'emp_appraisal_manager_rel', 'hr_appraisal_id')
    appraisal_manager_survey_id = fields.Many2one('survey.survey', string="Manager's Appraisal")
    appraisal_by_colleagues = fields.Boolean(string='Colleagues')
    appraisal_colleagues_ids = fields.Many2many('hr.employee', 'emp_appraisal_colleagues_rel', 'hr_appraisal_id')
    appraisal_colleagues_survey_id = fields.Many2one('survey.survey', string="Employee's Appraisal")
    appraisal_self = fields.Boolean(string='Employee')
    appraisal_employee = fields.Char(string='Employee Name')
    appraisal_self_survey_id = fields.Many2one('survey.survey', string='Self Appraisal')
    appraisal_by_collaborators = fields.Boolean(string='Collaborators')
    appraisal_collaborators_ids = fields.Many2many('hr.employee', 'emp_appraisal_subordinates_rel', 'hr_appraisal_id')
    appraisal_collaborators_survey_id = fields.Many2one('survey.survey', string="collaborate's Appraisal")
    periodic_appraisal = fields.Boolean(string='Periodic Appraisal', default=False)
    periodic_appraisal_created = fields.Boolean(string='Periodic Appraisal has been created', default=False)  # Flag for the cron
    appraisal_frequency = fields.Integer(string='Repeat Every', default=1)
    appraisal_frequency_unit = fields.Selection([('year', 'Year'), ('month', 'Month')], string='Repeat Every', copy=False, default='year')
    appraisal_count = fields.Integer(compute='_compute_appraisal_count', string='Appraisals')
    related_partner_id = fields.Many2one('res.partner', compute='_compute_related_partner')

    @api.multi
    def _compute_appraisal_count(self):
        appraisal = self.env['hr.appraisal'].read_group([('employee_id', 'in', self.ids)], ['employee_id'], ['employee_id'])
        result = dict((data['employee_id'][0], data['employee_id_count']) for data in appraisal)
        for employee in self:
            employee.appraisal_count = result.get(employee.id, 0)

    @api.one
    def _compute_related_partner(self):
        self.related_partner_id = self.user_id.partner_id

    @api.onchange('appraisal_by_manager', 'parent_id')
    def onchange_manager_appraisal(self):
        if self.appraisal_by_manager and self.parent_id:
            self.appraisal_manager_ids = [self.parent_id.id]
        else:
            self.appraisal_manager_ids = False

    @api.onchange('appraisal_self')
    def onchange_self_employee(self):
        if self.appraisal_self:
            self.appraisal_employee = self.name
        else:
            self.appraisal_employee = False

    @api.onchange('appraisal_by_colleagues')
    def onchange_colleagues(self):
        if self.appraisal_by_colleagues and self.department_id:
            self.appraisal_colleagues_ids = self.search([('department_id', '=', self.department_id.id), ('id', '!=', self._origin.id)])
        else:
            self.appraisal_colleagues_ids = False

    @api.onchange('appraisal_by_collaborators')
    def onchange_subordinates(self):
        if self.appraisal_by_collaborators:
            self.appraisal_collaborators_ids = self.child_ids
        else:
            self.appraisal_collaborators_ids = False

    @api.multi
    def write(self, vals):
        if vals.get('appraisal_date') and fields.Date.from_string(vals.get('appraisal_date')) < datetime.date.today():
            raise UserError(_("The date of the next appraisal cannot be in the past"))
        else:
            return super(HrEmployee, self).write(vals)

    @api.model
    def run_employee_appraisal(self, automatic=False, use_new_cursor=False):  # cronjob
        current_date = datetime.date.today()
        # Set the date of the next appraisal to come if the date is passed:
        for employee in self.search([('periodic_appraisal', '=', True), ('appraisal_date', '<=', current_date)]):
            months = employee.appraisal_frequency if employee.appraisal_frequency_unit == 'month' else employee.appraisal_frequency * 12
            employee.write({
                'appraisal_date': fields.Date.to_string(current_date + relativedelta(months=months)),
                'periodic_appraisal_created': False
            })
        # Create perdiodic appraisal if appraisal date is in less than a week adn the appraisal for this perdiod has not been created yet:
        for employee in self.search([
            ('periodic_appraisal', '=', True),
            ('periodic_appraisal_created', '=', False),
            ('appraisal_date', '<=', current_date + relativedelta(days=8)),
            ('appraisal_date', '>=', current_date),
        ]):

            vals = {'employee_id': employee.id,
                    'date_close': employee.appraisal_date,
                    'manager_appraisal': employee.appraisal_by_manager,
                    'manager_ids': [(4, manager.id) for manager in employee.appraisal_manager_ids],
                    'manager_survey_id': employee.appraisal_manager_survey_id.id,
                    'colleagues_appraisal': employee.appraisal_by_colleagues,
                    'colleagues_ids': [(4, colleagues.id) for colleagues in employee.appraisal_colleagues_ids],
                    'colleagues_survey_id': employee.appraisal_colleagues_survey_id.id,
                    'employee_appraisal': employee.appraisal_self,
                    'employee_survey_id': employee.appraisal_self_survey_id.id,
                    'collaborators_appraisal': employee.appraisal_by_collaborators,
                    'collaborators_ids': [(4, subordinates.id) for subordinates in employee.appraisal_collaborators_ids],
                    'collaborators_survey_id': employee.appraisal_collaborators_survey_id.id}
            self.env['hr.appraisal'].create(vals)
            employee.periodic_appraisal_created = True
