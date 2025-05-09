# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _get_default_crm_survey_template_id(self):
        return self.env.ref('crm_survey.lead_qualification_survey_template', raise_if_not_found=False)

    crm_survey_template_id = fields.Many2one('survey.survey')
