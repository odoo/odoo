from odoo import api, fields, models
from odoo.addons import base


class ResPartner(models.Model, base.ResPartner):

    ubl_cii_format = fields.Selection(selection_add=[('ciusro', "CIUSRO")])

    @api.depends('country_code')
    def _compute_ubl_cii_format(self):
        super()._compute_ubl_cii_format()
        for partner in self:
            if partner.country_code == 'RO':
                partner.ubl_cii_format = 'ciusro'

    def _get_edi_builder(self):
        if self.ubl_cii_format == 'ciusro':
            return self.env['account.edi.xml.ubl_ro']
        return super()._get_edi_builder()
