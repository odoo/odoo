from odoo import fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    origin_survey_id = fields.Many2one(
        comodel_name="survey.survey",
        string="Survey",
        index="btree_not_null",
        ondelete="set null",
    )
