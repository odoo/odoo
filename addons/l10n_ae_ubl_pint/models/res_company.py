from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _peppol_modules_document_types(self):
        # EXTENDS account_peppol
        # Without this, an AE company registering as a Peppol receiver never declares itself
        # capable of receiving PINT-AE documents (billing/selfbilling) in the SMP capability
        # declaration sent by _peppol_register_sender_as_receiver - senders/receivers can't find
        # this company as a valid AE PINT recipient on the network.
        document_types = super()._peppol_modules_document_types()
        # Both the exact and the "*"-wildcard-suffixed variant are registered: Peppol AP/SMP
        # lookups for PINT customization IDs can match either form depending on the sender's own
        # implementation, and registering only the exact one has been observed to make this
        # company unreachable for senders that look up the wildcard form.
        document_types['l10n_ae_ubl_pint'] = {
            f"urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:peppol:pint:billing-1@ae-1{suffix}::2.1":
                "PINT AE UBL Invoice"
            for suffix in ('', '*')
        } | {
            f"urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:peppol:pint:billing-1@ae-1{suffix}::2.1":
                "PINT AE UBL CreditNote"
            for suffix in ('', '*')
        } | {
            f"urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:peppol:pint:selfbilling-1@ae-1{suffix}::2.1":
                "PINT AE UBL Self-Billing Invoice"
            for suffix in ('', '*')
        } | {
            f"urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:peppol:pint:selfbilling-1@ae-1{suffix}::2.1":
                "PINT AE UBL Self-Billing CreditNote"
            for suffix in ('', '*')
        }
        return document_types
