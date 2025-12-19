import re
import logging

from odoo import api, fields, models

PDP_identifier_re = re.compile(r'^([0-9]{9})(_[0-9]{14})?(_.+)?$')

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_pdp_send_to_ppf = fields.Boolean(
        string="Send to PPF",
        help="Activate Flux 1 regulatory data, Flux 6 mandatory statuses and Flux 10 e-reporting generation for this company.",
        default=True,
    )
    l10n_fr_pdp_pilot_phase = fields.Boolean(
        string="E-Invoicing Pilot Phase",
        help="Participate in the Pilot Phase of the French E-Invoicing. This way you are able to test it before it becomes mandatory.",
    )
    l10n_fr_pdp_annuaire_start_date = fields.Date(
        string="Annuaire Start Date",
        help="The date on which the company is registered on the annuaire for the French e-invoicing.",
    )
    l10n_fr_pdp_registered = fields.Boolean(
        string="Approved Platform Registerd",
        compute="_compute_l10n_fr_pdp_registered",
    )
    pdp_identifier = fields.Char(
        compute='_compute_pdp_identifier',
        inverse='_inverse_pdp_identifier',
    )

    @api.depends('peppol_eas', 'peppol_endpoint')
    def _compute_pdp_identifier(self):
        for record in self:
            partner = record.partner_id
            record.pdp_identifier = partner.peppol_endpoint if partner.peppol_eas == '0225' else False

    def _inverse_pdp_identifier(self):
        for record in self:
            match = PDP_identifier_re.match(record.pdp_identifier or '')
            siren = match and match.group(1)
            if not siren:
                continue
            siret = match.group(2)[1:] if match and match.group(2) else False  # Remove `_` at the start
            record.partner_id.write({
                'peppol_eas': '0225',
                'peppol_endpoint': record.pdp_identifier,  # Will be verified by `_check_peppol_fields` constraint
                'siret': siret or siren,
            })

    @api.depends('l10n_fr_pdp_annuaire_start_date', 'account_peppol_proxy_state')
    def _compute_l10n_fr_pdp_registered(self):
        for company in self:
            company.l10n_fr_pdp_registered = (
                company.account_peppol_proxy_state == 'receiver'
                and company.l10n_fr_pdp_annuaire_start_date
                and company.l10n_fr_pdp_annuaire_start_date <= fields.Date.context_today(self)
            )

    @api.model
    def _check_pdp_identifier(self, pdp_identifier, warning=False):
        return pdp_identifier and PDP_identifier_re.match(pdp_identifier)

    def _reset_peppol_configuration(self):
        # Extend `account_peppol` to reset PDP specific fields
        self.write({
            'l10n_fr_pdp_send_to_ppf': True,
            'l10n_fr_pdp_annuaire_start_date': False,
            'l10n_fr_pdp_pilot_phase': False,
        })
        super()._reset_peppol_configuration()

    def _peppol_supported_document_types(self):
        """Returns a flattened dictionary of all supported document types."""
        return {
            **super()._peppol_supported_document_types(),
            'urn:un:unece:uncefact:data:standard:CrossDomainAcknowledgementAndResponse:100::CrossDomainAcknowledgementAndResponse##urn:peppol:france:billing:cdv:1.0::D22B': "French CDAR (Lifecycle Messages)",
            'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017::2.1': "UBL V2.1 Invoice",
            'urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:cen.eu:en16931:2017::2.1': "UBL V2.1 CreditNote",
            'urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100::CrossIndustryInvoice##urn:cen.eu:en16931:2017::D16B': "CII",
            'urn:peppol:doctype:pdf+xml##urn:cen.eu:en16931:2017#conformant#urn:peppol:france:billing:Factur-X:1.0::D22B': "French Factur-X",
            'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:peppol:france:billing:cius:1.0::2.1': "UBL EN16931 French CIUS Invoice",
            'urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:cen.eu:en16931:2017#compliant#urn:peppol:france:billing:cius:1.0::2.1': "UBL EN16931 French CIUS CreditNote",
            'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#conformant#urn:peppol:france:billing:extended:1.0::2.1': "UBL EN16931 French CTC Extended Invoice",
            'urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:cen.eu:en16931:2017#conformant#urn:peppol:france:billing:extended:1.0::2.1': "UBL EN16931 French CTC Extended CreditNote",
            'urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100::CrossIndustryInvoice##urn:cen.eu:en16931:2017#compliant#urn:peppol:france:billing:cius:1.0::D22B': "UN/CEFACT EN16931 French CIUS",
            'urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100::CrossIndustryInvoice##urn:cen.eu:en16931:2017#conformant#urn:peppol:france:billing:extended:1.0::D22B': "UN/CEFACT EN16931 French CTC Extended",
        }

    def _l10n_fr_pdp_update_pilot_phase(self, value):
        self.ensure_one()
        pdp_user = self.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'pdp')[:1]
        if not pdp_user or self.account_peppol_proxy_state not in ('smp_registration', 'receiver'):
            return

        result = pdp_user._call_peppol_proxy(
            "/api/pdp/1/pilot_phase",
            params={
                'pdp_pilot_phase': value,
            },
        )
        if 'error' in result:
            error_message = result['error'].get('message') or result['error'].get('data', {}).get('message')
            _logger.error('Error while updating pilot phase: %s', error_message)
            return

        pdp_user._peppol_process_participant_status(result)
