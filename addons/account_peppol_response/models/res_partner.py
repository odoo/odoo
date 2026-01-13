from odoo import api, fields, models
from odoo.addons.account_peppol.tools.demo_utils import handle_demo

INVOICE_RESPONSE_CUSTOMISATION_ID = "busdox-docid-qns::urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2::ApplicationResponse##urn:fdc:peppol.eu:poacc:trns:invoice_response:3::2.1"


class ResPartner(models.Model):
    _inherit = 'res.partner'

    peppol_supported_documents = fields.Json('Supported Peppol Documents')
    peppol_response_support = fields.Boolean('Peppol Response Service', compute='_compute_response_support')

    @api.depends('peppol_supported_documents', 'peppol_verification_state')
    def _compute_response_support(self):
        for partner in self:
            partner.peppol_response_support = (
                partner.peppol_verification_state == 'valid'
                and partner.peppol_supported_documents
                and INVOICE_RESPONSE_CUSTOMISATION_ID in partner.peppol_supported_documents
            )

    def _peppol_fill_participant_supported_documents(self):
        for partner in self:
            edi_identification = f"{partner.peppol_eas}:{partner.peppol_endpoint}".lower()
            participant_info = partner._peppol_lookup_participant(edi_identification)
            if not participant_info:
                continue
            partner.peppol_supported_documents = [service['document_id'] for service in participant_info.get('services', []) if service.get('document_id')]

    @handle_demo
    def button_account_peppol_check_partner_endpoint(self, company=None):
        # EXTENDS account_peppol
        self.ensure_one()
        super().button_account_peppol_check_partner_endpoint(company)

        if not company:
            company = self.env.company
        self_partner = self.with_company(company)
        if self_partner.peppol_eas and self_partner.peppol_endpoint:
            self_partner._peppol_fill_participant_supported_documents()
        return False
