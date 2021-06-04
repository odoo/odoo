# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    applicant_skill_ids = fields.Many2many('hr.skill', compute='_compute_applicant_skills', store=True)

    @api.depends('application_ids.skill_ids', 'application_ids')
    def _compute_applicant_skills(self):
        for partner in self:
            partner.applicant_skill_ids = partner.application_ids.skill_ids
