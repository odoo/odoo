from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _peppol_modules_document_types(self):
        # EXTENDS 'account_peppol'
        return super()._peppol_modules_document_types() | {
            'account_peppol_selfbilling': {
                "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:selfbilling:3.0::2.1": "Peppol BIS Self-Billing UBL Invoice V3",
                "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:selfbilling:3.0::2.1": "Peppol BIS Self-Billing UBL CreditNote V3",
            }
        }
