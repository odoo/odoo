# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests
from lxml import etree
from markupsafe import Markup
from hashlib import md5
from urllib import parse

from odoo import api, fields, models
from odoo.addons.account_edi_ubl_cii.models.account_edi_common import EAS_MAPPING
from odoo.addons.account_peppol.tools.demo_utils import handle_demo
from odoo.addons.account.models.company import PEPPOL_LIST

TIMEOUT = 10
_logger = logging.getLogger(__name__)



class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_sending_method = fields.Selection(
        selection_add=[('peppol', 'by Peppol')],
    )
    peppol_eas = fields.Selection(selection_add=[('odemo', 'Odoo Demo ID')])  # Not a real EAS, used for demonstration.
    available_peppol_sending_methods = fields.Json(compute='_compute_available_peppol_sending_methods')
    available_peppol_edi_formats = fields.Json(compute='_compute_available_peppol_edi_formats')
    peppol_verification_state = fields.Selection(
        selection=[
            ('not_verified', 'Not verified yet'),
            ('not_valid', 'Not on Peppol'),  # does not exist on Peppol at all
            ('not_valid_format', 'Cannot receive this format'),  # registered on Peppol but cannot receive the selected document type
            ('valid', 'Valid'),
        ],
        store=True,
        string='Peppol endpoint verification',
        company_dependent=True,
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends_context('company')
    @api.depends('company_id')
    def _compute_available_peppol_sending_methods(self):
        methods = dict(self._fields['invoice_sending_method'].selection)
        if self.env.company.country_code not in PEPPOL_LIST:
            methods.pop('peppol')
        self.available_peppol_sending_methods = list(methods)

    @api.depends_context('company')
    @api.depends('invoice_sending_method')
    def _compute_available_peppol_edi_formats(self):
        for partner in self:
            if partner.invoice_sending_method == 'peppol':
                partner.available_peppol_edi_formats = self._get_peppol_formats()
            else:
                partner.available_peppol_edi_formats = list(dict(self._fields['invoice_edi_format'].selection))

    def _compute_available_peppol_eas(self):
        # EXTENDS 'account_edi_ubl_cii'
        super()._compute_available_peppol_eas()
        eas_codes = set(self.available_peppol_eas)
        if self.env.company._get_peppol_edi_mode() != 'demo' and 'odemo' in eas_codes:
            eas_codes.remove('odemo')
            self.available_peppol_eas = list(eas_codes)

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _log_verification_state_update(self, company, old_value, new_value):
        # log the update of the peppol verification state
        # we do this instead of regular tracking because of the customized message
        # and because we want to log the change for every company in the db
        if old_value == new_value:
            return

        peppol_verification_state_field = self._fields['peppol_verification_state']
        selection_values = dict(peppol_verification_state_field.selection)
        old_label = selection_values[old_value] if old_value else False  # get translated labels
        new_label = selection_values[new_value] if new_value else False
        invoice_edi_format_field = self._fields['invoice_edi_format']
        format_selection_values = dict(invoice_edi_format_field.selection)
        edi_format = format_selection_values[self._get_peppol_edi_format()]

        body = Markup("""
            <ul>
                <li>
                    <span class='o-mail-Message-trackingOld me-1 px-1 text-muted fw-bold'>{old}</span>
                    <i class='o-mail-Message-trackingSeparator fa fa-long-arrow-right mx-1 text-600'/>
                    <span class='o-mail-Message-trackingNew me-1 fw-bold text-info'>{new}</span>
                    <span class='o-mail-Message-trackingField ms-1 fst-italic text-muted'>{format}</span>
                </li>
            </ul>
        """).format(
            old=old_label,
            new=new_label,
            format=f'({edi_format})' if new_value == 'not_valid_format' else '',
        )
        self._message_log(body=body)

    @api.model
    def _get_participant_info(self, edi_identification):
        hash_participant = md5(edi_identification.lower().encode()).hexdigest()
        endpoint_participant = parse.quote_plus(f"iso6523-actorid-upis::{edi_identification}")
        edi_mode = self.env.company._get_peppol_edi_mode()
        sml_zone = 'acc.edelivery' if edi_mode == 'test' else 'edelivery'
        smp_url = f"http://B-{hash_participant}.iso6523-actorid-upis.{sml_zone}.tech.ec.europa.eu/{endpoint_participant}"

        try:
            response = requests.get(smp_url, timeout=TIMEOUT)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.debug(e)
            return None
        return etree.fromstring(response.content)

    @api.model
    @handle_demo
    def _check_peppol_participant_exists(self, participant_info, edi_identification):
        participant_identifier = participant_info.findtext('{*}ParticipantIdentifier')
        service_metadata = participant_info.find('.//{*}ServiceMetadataReference')
        service_href = ''
        if service_metadata is not None:
            service_href = service_metadata.attrib.get('href', '')

        if edi_identification != participant_identifier or 'hermes-belgium' in service_href:
            # all Belgian companies are pre-registered on hermes-belgium, so they will
            # technically have an existing SMP url but they are not real Peppol participants
            return False

        return True

    def _check_document_type_support(self, participant_info, ubl_cii_format):
        service_references = participant_info.findall(
            '{*}ServiceMetadataReferenceCollection/{*}ServiceMetadataReference'
        )
        document_type = self.env['account.edi.xml.ubl_21']._get_customization_ids()[ubl_cii_format]
        for service in service_references:
            if document_type in parse.unquote_plus(service.attrib.get('href', '')):
                return True
        return False

    def _update_peppol_state_per_company(self, vals=None):
        partners = self.env['res.partner']
        if vals is None:
            partners = self.filtered(lambda p: all([p.peppol_eas, p.peppol_endpoint, p.is_ubl_format, p.country_code in PEPPOL_LIST]))
        elif {'peppol_eas', 'peppol_endpoint', 'invoice_edi_format'}.intersection(vals.keys()):
            partners = self.filtered(lambda p: p.country_code in PEPPOL_LIST)

        all_companies = None
        for partner in partners.sudo():
            if partner.company_id:
                partner.button_account_peppol_check_partner_endpoint(company=partner.company_id)
                continue

            if all_companies is None:
                # We only check it for companies that are actually using Peppol.
                can_send = self.env['account_edi_proxy_client.user']._get_can_send_domain()
                all_companies = self.env['res.company'].sudo().search([
                    ('account_peppol_proxy_state', 'in', can_send),
                ])

            for company in all_companies:
                partner.button_account_peppol_check_partner_endpoint(company=company)

    def _peppol_try_other_eas(self, eas_to_check, invoice_edi_format):
        """
        This method is called when the user checks the peppol endpoint for a partner, and that it's not found.
        We try the other eas available for this country, following the mapping in EAS_MAPPING.
        :param eas_to_check: A list of eas code to try to find the user.
        :param edi_format:
        :return: The eas code for which the user was found, or False if the user is still not found.
        """
        for eas, field in eas_to_check.items():
            if field and self._get_peppol_verification_state(self[field], eas, invoice_edi_format) == 'valid':
                return self[field], eas, 'valid'
        return False, False, 'not_valid'

    def _get_eas_mapping(self, eas, include_given_eas=True):
        """
        This method is called to get the eas mappings for a given eas code
        :param eas:                 The eas code we search the mappings for
        :param include_given_eas:   bool if the returned dictionnary should contains the eas given as a parameter
        :return: A dict containing the eas mappings for the given eas code
        """
        # get mappings based on the partner country and check the given eas is inside
        mappings = dict(EAS_MAPPING.get(self.country_code, {}))
        if not mappings or not mappings.get(eas):
            # get mappings based on eas
            mappings = [country for country in EAS_MAPPING.values() if country.get(eas)]
            mappings = mappings[0] if mappings else False
        if mappings and not include_given_eas:
            del mappings[eas]
        return mappings

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if res:
            res._update_peppol_state_per_company()
        return res

    def write(self, vals):
        # OVERRIDE
        old_verification_state = None
        company = self.env.company
        if ('peppol_eas' in vals or 'peppol_endpoint' in vals
                and self.peppol_verification_state != 'not_verified'
                and not vals.get('peppol_verification_state')):
            # reset the verification state to not have new combination flagged as anything else than 'not verified'
            old_verification_state = self.with_company(company).peppol_verification_state
            vals['peppol_verification_state'] = 'not_verified'
        res = super().write(vals)
        if res and old_verification_state:
            self._log_verification_state_update(self.env.company, old_verification_state, vals.get('peppol_verification_state'))
        return res

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def button_account_peppol_check_partner_endpoint(self, company=None):
        """ A basic check for whether a participant is reachable at the given
        Peppol participant ID - peppol_eas:peppol_endpoint (ex: '9999:test')
        The SML (Service Metadata Locator) assigns a DNS name to each peppol participant.
        This DNS name resolves into the SMP (Service Metadata Publisher) of the participant.
        The DNS address is of the following form:
        - "http://B-" + hexstring(md5(lowercase(ID-VALUE))) + "." + ID-SCHEME + "." + SML-ZONE-NAME + "/" + url_encoded(ID-SCHEME + "::" + ID-VALUE)
        (ref:https://peppol.helger.com/public/locale-en_US/menuitem-docs-doc-exchange)
        """
        self.ensure_one()
        if not company:
            company = self.env.company

        self_partner = self.with_company(company)
        old_value = self_partner.peppol_verification_state
        new_value = self._get_peppol_verification_state(
            self.peppol_endpoint,
            self.peppol_eas,
            self_partner._get_peppol_edi_format(),
        )

        if new_value in ('not_valid', 'not_valid_format'):
            eas_to_try = self._get_eas_mapping(eas=self.peppol_eas, include_given_eas=False)
            if eas_to_try:
                new_endpoint, new_eas, new_peppol_verification_state = self._peppol_try_other_eas(eas_to_try, self_partner._get_peppol_edi_format())
                if new_peppol_verification_state == 'valid':
                    new_value = new_peppol_verification_state
                    self.write({
                        'peppol_eas': new_eas,
                        'peppol_endpoint': new_endpoint,
                    })

        if old_value != new_value:
            self_partner.peppol_verification_state = new_value
            self._log_verification_state_update(company, old_value, self_partner.peppol_verification_state)
        return False

    @api.model
    @handle_demo
    def _get_peppol_verification_state(self, peppol_endpoint, peppol_eas, invoice_edi_format):
        if not (peppol_eas and peppol_endpoint) or invoice_edi_format not in self._get_peppol_formats():
            return 'not_verified'

        edi_identification = f"{peppol_eas}:{peppol_endpoint}".lower()
        participant_info = self._get_participant_info(edi_identification)
        if participant_info is None:
            return 'not_valid'
        else:
            is_participant_on_network = self._check_peppol_participant_exists(participant_info, edi_identification)
            if is_participant_on_network:
                is_valid_format = self._check_document_type_support(participant_info, invoice_edi_format)
                if is_valid_format:
                    return 'valid'
                else:
                    return 'not_valid_format'
            else:
                return 'not_valid'

    def _get_frontend_writable_fields(self):
        frontend_writable_fields = super()._get_frontend_writable_fields()
        frontend_writable_fields.update({'peppol_eas', 'peppol_endpoint'})

        return frontend_writable_fields
