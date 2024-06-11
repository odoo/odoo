from odoo import api, models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ubl_cii_format = fields.Selection(selection_add=[('oioubl_201', "OIOUBL 2.01")])

    def _get_edi_builder(self):
        if self.ubl_cii_format == 'oioubl_201':
            return self.env['account.edi.xml.oioubl_201']
        return super()._get_edi_builder()

    @api.depends('country_code')
    def _compute_ubl_cii_format(self):
        super()._compute_ubl_cii_format()
        for partner in self:
            if partner.country_code == 'DK':
                partner.ubl_cii_format = 'oioubl_201'
