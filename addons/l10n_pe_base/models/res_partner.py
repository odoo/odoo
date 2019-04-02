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
          0 - Non-Domiciled Tax Document without RUC
        * 1 - National Identity Document (DNI, Spanish acronym)
        * 4 - Alien Registration Card
        * 6 - Single Taxpayer Registration (RUC, Spanish acronym)
        * 7 - Passport
        * A - Diplomatic Identity Card
        * B - Identity document of the country of residence
        * C - Tax Identification Number - TIN
        * D - Identification Number - IN
        * E - Andean Immigration Card (TAM, Spanish acronym)

        this represent the catalog no. 6 of SUNAT (1)
        http://cpe.sunat.gob.pe/sites/default/files/inline-files/anexoV-340-2017.pdf
        (*) types are supported in odoo core module base_vat
        """
        self.ensure_one()
        if self.country_id != self.env.ref('base.pe'):
            return {"vat_number": self.vat, "vat_code": '0'}
        if not self.vat:
            return {"vat_type": 'D', "vat_number": '00000000', "vat_code": '1'}
        vat_number = self._split_vat(self.vat)[1]
        vat_type, vat_number = vat_number[0], vat_number[1:]
        vat_codes = {'R': '6', 'D': '1', 'P': '7', 'E': '4',
                     'C': 'A', 'B': 'B', 'T': 'C', 'I': 'D', 'A': 'E'}
        vat_code = vat_codes.get(vat_type)
        return {"vat_type": vat_type, "vat_number": vat_number,
                "vat_code": vat_code}
