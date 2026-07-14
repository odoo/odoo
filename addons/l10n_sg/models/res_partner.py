# -*- coding: utf-8 -*-

from odoo import fields, models

class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    l10n_sg_unique_entity_number = fields.Char(string='UEN')

    def _deduce_country_code(self):
        if self.l10n_sg_unique_entity_number:
            return 'SG'
        return super()._deduce_country_code()

    def _peppol_eas_endpoint_depends(self):
        # extends account_edi_ubl_cii
        return super()._peppol_eas_endpoint_depends() + ['l10n_sg_unique_entity_number']
