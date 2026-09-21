from odoo import fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    tier_id = fields.Many2one(
        comodel_name="partner.tier",
        related="partner_id.commercial_partner_id.tier_id",
        string="Commercial Tier",
        help="The commercial tier of the customer this lead names; the pipeline "
        "groups by it and predictive lead scoring can read it.",
    )
