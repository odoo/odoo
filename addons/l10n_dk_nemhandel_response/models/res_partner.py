from odoo import api, fields, models
from odoo.addons.l10n_dk_nemhandel.tools.demo_utils import handle_demo

APPLICATION_RESPONSE_CUSTOMISATION_ID = "busdox-docid-qns::urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2::ApplicationResponse##OIOUBL-2.1::2.1"


class ResPartner(models.Model):
    _inherit = 'res.partner'

    nemhandel_supported_documents = fields.Json('Supported Nemhandel Documents')
    nemhandel_response_support = fields.Boolean('Nemhandel Response Service', compute='_compute_nemhandel_response_support')

    @api.depends('nemhandel_supported_documents', 'nemhandel_verification_state')
    def _compute_nemhandel_response_support(self):
        for partner in self:
            partner.nemhandel_response_support = (
                partner.nemhandel_verification_state == 'valid'
                and partner.nemhandel_supported_documents
                and APPLICATION_RESPONSE_CUSTOMISATION_ID in partner.nemhandel_supported_documents
            )

    def _nemhandel_fill_participant_supported_documents(self):
        self.ensure_one()
        edi_identification = f"{self.nemhandel_identifier_type}:{self.nemhandel_identifier_value}".lower()
        participant_info = self._nemhandel_lookup_participant(edi_identification)
        if not participant_info:
            return
        self.nemhandel_supported_documents = [service['document_id'] for service in participant_info.get('services', []) if service.get('document_id')]

    @handle_demo
    def button_nemhandel_check_partner_endpoint(self, company=None):
        # EXTENDS l10n_dk_nemhandel
        self.ensure_one()
        super().button_nemhandel_check_partner_endpoint(company)

        if not company:
            company = self.env.company
        self_partner = self.with_company(company)
        self_partner._nemhandel_fill_participant_supported_documents()
        return False
