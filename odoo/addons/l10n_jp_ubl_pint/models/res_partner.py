from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ubl_cii_format = fields.Selection(selection_add=[('pint_jp', "PINT Japan")])

    def _get_edi_builder(self):
        # EXTENDS 'account_edi_ubl_cii'
        if self.ubl_cii_format == 'pint_jp':
            return self.env['account.edi.xml.pint_jp']
        return super()._get_edi_builder()

    def _compute_ubl_cii_format(self):
        # EXTENDS 'account_edi_ubl_cii'
        super()._compute_ubl_cii_format()
        for partner in self:
            if partner.country_code == 'JP':
                partner.ubl_cii_format = 'pint_jp'
