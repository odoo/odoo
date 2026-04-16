from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    sst_registration_number = fields.Char(
        string="SST",
        help="Malaysian Sales and Service Tax Number",
    )
    ttx_registration_number = fields.Char(
        string="TTx",
        help="Malaysian Tourism Tax Number",
    )

    def _compute_is_company(self):
        super()._compute_is_company()
        for partner in self:
            if partner.country_code == 'MY' and partner.is_company and partner.vat.upper().startswith("IG"):
                partner.is_company = False

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['sst_registration_number', 'ttx_registration_number']
