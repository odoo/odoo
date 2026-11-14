from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _peppol_modules_document_types(self):
        document_types = super()._peppol_modules_document_types()
        document_types['l10n_sg_sale_peppol'] = {
            "urn:oasis:names:specification:ubl:schema:xsd:Order-2::Order##urn:fdc:peppol.eu:poacc:trns:order:3::2.1":
                "Peppol BIS Ordering Order 3.0",
            "urn:oasis:names:specification:ubl:schema:xsd:OrderChange-2::OrderChange##urn:fdc:peppol.eu:poacc:trns:order_change:3::2.3":
                "Peppol BIS Advanced Ordering OrderChange 3.0",
            "urn:oasis:names:specification:ubl:schema:xsd:OrderCancellation-2::OrderCancellation##urn:fdc:peppol.eu:poacc:trns:order_cancellation:3::2.3":
                "Peppol BIS Advanced Ordering OrderCancellation 3.0",
            "urn:oasis:names:specification:ubl:schema:xsd:Order-2::Order##urn:fdc:imda.gov.sg:trns:order_balance:1::2.1":
                "IMDA Singapore Order Balance 1.0",
        }
        return document_types
