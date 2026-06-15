from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _inverse_peppol_purchase_journal_id(self):
        # If the user removed his Import journal in his Peppol settings, we need to tell IAP the user can't support
        # responses anymore. If a journal is added when it was empty before, we also need to tell IAP the user can support
        # responses again.
        super()._inverse_peppol_purchase_journal_id()
        if cron := self.env.ref('account_peppol_response.ir_cron_peppol_auto_register_services', raise_if_not_found=False):
            cron._trigger()

    def _peppol_modules_document_types(self):
        document_types = super()._peppol_modules_document_types()
        document_types['account_peppol_response'] = {
            "urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2::ApplicationResponse##urn:fdc:peppol.eu:poacc:trns:invoice_response:3::2.1":
                "Peppol Invoice Response transaction 3.0",
        }
        return document_types
