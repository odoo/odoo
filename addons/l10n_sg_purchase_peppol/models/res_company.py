from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _peppol_modules_document_types(self):
        document_types = super()._peppol_modules_document_types()
        document_types['l10n_sg_purchase_peppol'] = {
            "urn:oasis:names:specification:ubl:schema:xsd:OrderResponse-2::OrderResponse##urn:fdc:peppol.eu:poacc:trns:order_response_advanced:3::2.3":
                "Peppol BIS Advanced Ordering OrderResponse Advanced 3.0",
        }
        return document_types
