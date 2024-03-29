# coding: utf-8
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_no_bronnoysund_number = fields.Char(string='Register of Legal Entities (Brønnøysund Register Center)', size=9)

    def _deduce_country_code(self):
        if self.l10n_no_bronnoysund_number:
            return 'NO'
        return super()._deduce_country_code()

    def _peppol_eas_endpoint_depends(self):
        # extends account_edi_ubl_cii
        return super()._peppol_eas_endpoint_depends() + ['l10n_no_bronnoysund_number']
