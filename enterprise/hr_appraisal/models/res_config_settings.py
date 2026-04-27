# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    appraisal_plan = fields.Boolean(related='company_id.appraisal_plan', readonly=False)
    appraisal_template_id = fields.Many2one(related='company_id.appraisal_template_id', readonly=False, check_company=True)
    assessment_note_ids = fields.One2many(
        related='company_id.assessment_note_ids', string="Evaluation Scale", readonly=False)

    duration_after_recruitment = fields.Integer(related='company_id.duration_after_recruitment', readonly=False)
    duration_first_appraisal = fields.Integer(related='company_id.duration_first_appraisal', readonly=False)
    duration_next_appraisal = fields.Integer(related='company_id.duration_next_appraisal', readonly=False)

    module_hr_appraisal_survey = fields.Boolean(string="360 Feedback")
