# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ubl_cii_format = fields.Selection(selection_add=[('pint_my', "PINT Malaysia")])
    sst_registration_number = fields.Char(
        string="SST",
        help="Malaysian Sales and Service Tax Number",
    )
    ttx_registration_number = fields.Char(
        string="TTx",
        help="Malaysian Tourism Tax Number",
    )

    def _get_edi_builder(self):
        # EXTENDS 'account_edi_ubl_cii'
        if self.ubl_cii_format == 'pint_my':
            return self.env['account.edi.xml.pint_my']
        return super()._get_edi_builder()

    def _compute_ubl_cii_format(self):
        # EXTENDS 'account_edi_ubl_cii'
        super()._compute_ubl_cii_format()
        for partner in self:
            if partner.country_code == 'MY':
                partner.ubl_cii_format = 'pint_my'

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['sst_registration_number', 'ttx_registration_number']
