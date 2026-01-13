from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _peppol_modules_document_types(self):
        document_types = super()._peppol_modules_document_types()
        document_types['account_peppol_response'] = {
            "urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2::ApplicationResponse##urn:fdc:peppol.eu:poacc:trns:invoice_response:3::2.1":
                "Peppol Invoice Response transaction 3.0",
        }
        return document_types
