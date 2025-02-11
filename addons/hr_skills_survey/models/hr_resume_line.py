# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class ResumeLine(models.Model):
    _inherit = 'hr.resume.line'

    display_type = fields.Selection(selection_add=[('certification', 'Certification')])
    department_id = fields.Many2one(related="employee_id.department_id", store=True)
    survey_id = fields.Many2one('survey.survey', string='Certification', readonly=True)
    expiration_status = fields.Selection([
        ('expired', 'Expired'),
        ('expiring', 'Expiring'),
        ('valid', 'Valid')], compute='_compute_expiration_status', store=True)

    @api.depends('date_end')
    def _compute_expiration_status(self):
        self.expiration_status = 'valid'
        for line in self:
            if line.date_end:
                if line.date_end <= fields.Date.today():
                    line.expiration_status = 'expired'
                elif line.date_end + relativedelta(months=-3) <= fields.Date.today():
                    line.expiration_status = 'expiring'
