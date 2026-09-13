from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    account_edi_proxy_client_ids = fields.One2many(
        comodel_name="account_edi_proxy_client.user",
        inverse_name="company_id",
        context={"active_test": True},
    )
