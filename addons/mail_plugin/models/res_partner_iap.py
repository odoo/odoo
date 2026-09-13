from odoo import fields, models


class ResPartnerIap(models.Model):
    _name = "res.partner.iap"
    _description = "Partner IAP"

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        required=True,
        ondelete="cascade",
    )
    iap_search_domain = fields.Char(
        string="Search Domain / Email",
        help="Domain used to find the company",
    )
    iap_enrich_info = fields.Text(
        string="IAP Enrich Info",
        readonly=True,
        help="IAP response stored as a JSON string",
    )

    _unique_partner_id = models.Constraint(
        "UNIQUE(partner_id)",
        "Only one partner IAP is allowed for one partner",
    )
