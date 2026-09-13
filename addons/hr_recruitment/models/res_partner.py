from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    applicant_ids = fields.One2many(
        comodel_name="hr.applicant",
        inverse_name="partner_id",
        string="Applicants",
    )
