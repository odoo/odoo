# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    skill_ids = fields.Many2many('hr.skill', string='Skills')

    @api.model
    def _get_applicant_fields(self):
        return ['name', 'description', 'email_from', 'partner_id', 'company_id']
