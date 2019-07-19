# Copyright 2019 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_pe_edi_district = fields.Many2one(
        'res.district', string='District',
        help='Districts are part of a province or city.')

    @api.multi
    def l10n_pe_edi_get_customer_vat(self):
        """Based on current vat validation and implementation, the following
        logic set the code associated and its vat without prefix
        chat on its vat field.
          0 - Documento Tributario No Domiciliado Sin RUC
        * 1 - Documento Nacional de Identidad
          4 - Carnet de Extranjería
        * 6 - Registro Único de Contribuyentes
          7 - Pasaporte
          A - Cédula Diplomática de Identidad

        this represent the catalog no. 6 of SUNAT (1)
        https://www.vauxoo.com/r/catalogosSUNAT
        (*) types are supported in odoo core module base_vat
        """
        self.ensure_one()
        if self.country_id != self.env.ref('base.pe'):
            return {"vat_number": self.vat, "vat_code": '0'}
        if not self.vat:
            return {"vat_type": 'D', "vat_number": '00000000', "vat_code": '1'}
        vat_number = self._split_vat(self.vat)[1]
        vat_type, vat_number = vat_number[0], vat_number[1:]
        vat_codes = {'R': '6', 'D': '1'}
        vat_code = vat_codes.get(vat_type)
        return {"vat_type": vat_type, "vat_number": vat_number,
                "vat_code": vat_code}
