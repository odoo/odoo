# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _peppol_modules_document_types(self):
        document_types = super()._peppol_modules_document_types()
        document_types['l10n_sg_ubl_pint'] = {
            "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:peppol:pint:billing-1@sg-1::2.1":
                "SG PINT Invoice",
            "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:peppol:pint:billing-1@sg-1::2.1":
                "SG PINT CreditNote",
        }
        return document_types
