# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ubl_cii_format = fields.Selection(selection_add=[('pint_sg', "PINT Singapore")])

    def _get_edi_builder(self):
        # EXTENDS 'account_edi_ubl_cii'
        if self.ubl_cii_format == 'pint_sg':
            return self.env['account.edi.xml.pint_sg']
        return super()._get_edi_builder()

    def _compute_ubl_cii_format(self):
        # EXTENDS 'account_edi_ubl_cii'
        super()._compute_ubl_cii_format()
        for partner in self:
            if partner.country_code == 'SG':
                partner.ubl_cii_format = 'pint_sg'
