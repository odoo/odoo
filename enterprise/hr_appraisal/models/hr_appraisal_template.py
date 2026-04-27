# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class HrAppraisal(models.Model):
    _name = "hr.appraisal.template"
    _description = "Employee Appraisal Template"
    _rec_name = 'description'

    description = fields.Char(required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    appraisal_employee_feedback_template = fields.Html('Employee Feedback', store=True, readonly=False, translate=True)
    appraisal_manager_feedback_template = fields.Html('Manager Feedback', store=True, readonly=False, translate=True)

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, description=_("%s (copy)", template.description)) for template, vals in zip(self, vals_list)]
