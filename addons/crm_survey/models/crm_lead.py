from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Allows to filter lead qualifications from a survey
    survey_id = fields.Many2one('survey.survey')
