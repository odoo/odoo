from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Origin of the lead
    origin_survey_id = fields.Many2one('survey.survey', string='Survey', index='btree_not_null', ondelete='set null')
