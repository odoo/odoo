from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Origin of the lead
    # TODO awa: check if still necessary, could be replace with utm.reference
    origin_survey_id = fields.Many2one('survey.survey', string='Survey', index='btree_not_null', ondelete='set null')
