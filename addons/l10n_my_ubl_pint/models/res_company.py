from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"
    _inherits_sudo_fields = (
        "sst_registration_number",
        "ttx_registration_number",
    )


class BaseDocumentLayout(models.TransientModel):
    _inherit = "base.document.layout"

    account_fiscal_country_id = fields.Many2one(
        related="company_id.account_config_id.account_fiscal_country_id"
    )
    sst_registration_number = fields.Char(related="company_id.sst_registration_number")
    ttx_registration_number = fields.Char(related="company_id.ttx_registration_number")
