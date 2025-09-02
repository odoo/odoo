# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from markupsafe import Markup
from urllib import parse

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.addons.account.models.company import PEPPOL_LIST

TIMEOUT = 10
_logger = logging.getLogger(__name__)



class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_sending_method = fields.Selection(
        selection_add=[('peppol', 'by Peppol')],
    )
    peppol_alerts = fields.Json(compute='_compute_peppol_alerts')
    # TODO add odemo to list of identifiers
    available_peppol_sending_methods = fields.Json(compute='_compute_available_peppol_sending_methods')
    available_peppol_edi_formats = fields.Json(
        compute='_compute_available_peppol_edi_formats',
        store=True,
        readonly=True,
    )
    peppol_verification_state = fields.Selection(
        selection=[
            ('not_verified', 'Not verified yet'),
            ('not_applicable', 'Missing information'),  # we cannot check if the partner is on Peppol because we have no identifier
            ('not_valid', 'Partner is not on Peppol'),  # does not exist on Peppol at all
            ('not_valid_format', 'Partner is on Peppol but cannot receive any Odoo format'),
            ('valid', 'Partner is on Peppol'),
        ],
        string='Peppol endpoint verification',
    )
    peppol_last_sync = fields.Datetime(
        string='Last sync with Peppol',
    )
    peppol_identifier_ids = fields.One2many(
        comodel_name='res.partner.identification',
        compute='_compute_peppol_identifier_ids',
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('identifier_ids', 'peppol_verification_state', 'country_code')
    def _compute_peppol_alerts(self):
        for partner in self:
            alerts = {}
            if self.country_code == 'BE' and not self.peppol_identifier_ids.filtered(lambda i: i.code == 'BE:EN'):
                alerts['peppol_be_no_en'] = {
                    'level': 'error',
                    'message': self.env._("The mandatory identification method for Belgium is your Company Registry Number."),
                }
            if self.peppol_verification_state == 'valid' and not self.country_code:
                alerts['peppol_no_country'] = {
                    'level': 'error',
                    'message': self.env._("To generate complete electronic invoices, also set a country for this partner."),
                }
            partner.peppol_alerts = alerts

    @api.depends_context('company')
    @api.depends('company_id')
    def _compute_available_peppol_sending_methods(self):
        methods = dict(self._fields['invoice_sending_method'].selection)
        if self.env.company.country_code not in PEPPOL_LIST:
            methods.pop('peppol')
        self.available_peppol_sending_methods = list(methods)

    @api.depends('company_id')
    def _compute_available_peppol_edi_formats(self):
        for partner in self:
            partner.available_peppol_edi_formats = list(dict(self._fields['invoice_edi_format'].selection))

    @api.depends('identifier_ids')
    def _compute_peppol_identifier_ids(self):
        for partner in self:
            partner.peppol_identifier_ids = partner.identifier_ids.filtered(lambda i: i._is_peppol_registrable())

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

        body = Markup("""
            <ul>
                <li>
                    <span class='o-mail-Message-trackingOld me-1 px-1 text-muted fw-bold'>{old}</span>
                    <i class='o-mail-Message-trackingSeparator fa fa-long-arrow-right mx-1 text-600'/>
                    <span class='o-mail-Message-trackingNew me-1 fw-bold text-info'>{new}</span>
                    <span class='o-mail-Message-trackingField ms-1 fst-italic text-muted'>({field})</span>
                    <span class='o-mail-Message-trackingCompany ms-1 fst-italic text-muted'>({company})</span>
                </li>
            </ul>
        """).format(
            old=old_label,
            new=new_label,
            field=peppol_verification_state_field.string,
            company=company.display_name,
        )
        self._message_log(body=body)

    def _check_document_type_support(self, participant_info, ubl_cii_format):
        service_references = participant_info.findall(
            '{*}ServiceMetadataReferenceCollection/{*}ServiceMetadataReference'
        )
        document_type = self.env['account.edi.xml.ubl_21']._get_customization_ids()[ubl_cii_format]
        for service in service_references:
            if document_type in parse.unquote_plus(service.attrib.get('href', '')):
                return True
        return False

    def _get_main_endpoint(self):
        # EXTENDS 'account_edi_ubl_cii' - take Peppol registered endpoint first
        on_odoo_peppol = self.peppol_identifier_ids.filtered(lambda i: i.is_on_odoo_peppol)[:1]
        on_peppol = self.peppol_identifier_ids.filtered(lambda i: i.is_on_peppol)[:1]
        return on_odoo_peppol or on_peppol or super()._get_main_endpoint()

    def _sync_partners_peppol_info(self, force_sync=False, allow_raising=False):
        partners_to_update = self.env['res.partner']
        for partner in self:
            if not partner.peppol_identifier_ids:
                partner.peppol_verification_state = 'not_applicable'
                partner.available_peppol_edi_formats = list(dict(self._fields['invoice_edi_format'].selection))
                partner.peppol_last_sync = False
                continue

            sync_delay = -30 if partner.peppol_verification_state == 'valid' else -7
            last_sync_too_old = partner.peppol_last_sync <= fields.Datetime.add(fields.Datetime.now(), days=sync_delay)
            if force_sync or last_sync_too_old:
                partners_to_update |= partner

        if partners_to_update and (result := self._peppol_fetch_partner_info(allow_raising=allow_raising)):
            for partner in partners_to_update:
                is_on_peppol, main_endpoint = result[partner.id]['is_on_peppol'], result[partner.id]['main_endpoint']
                supported_services, external_provider = result[partner.id]['services'], result[partner.id]['provider']
                partner.peppol_verification_state = 'not_valid' if not is_on_peppol else ('valid' if supported_services else 'not_valid_format')
                partner.available_peppol_edi_formats = supported_services
                partner.peppol_last_sync = fields.Datetime.now()
                partner.external_provider = external_provider
                partner.identifier_ids.filtered(lambda i: i.iso_identifier == main_endpoint).is_on_peppol = True

    def _peppol_fetch_partner_info(self, company=False, allow_raising=False):
        company = company or self.env.company
        endpoint = '/api/peppol/1/_sync_peppol_partners'
        params = {
            partner.id: {
                'identifiers': partner.peppol_identifier_ids.mapped('iso_identifier'),
            }
            for partner in self
        }
        peppol_mode = company._get_peppol_edi_mode()  # FIXME should I find a smarter way to get the correct company ?
        response = self.env['account_edi_proxy_client.user']._call_peppol_proxy_public(
            endpoint,
            peppol_mode=peppol_mode,
            params=params,
        )
        if 'error' in response:
            if allow_raising:
                raise UserError(self.env._("Failed to contact Peppol Proxy. Please try again later."))
            return False
        return response['result']  # {partner_id: {'is_on_peppol': True, 'provider', 'ProviderName', 'services': ...}}

    def button_sync_partners_peppol_info(self, force_sync=True, notify=True):
        self._sync_partners_peppol_info(force_sync=force_sync, notify=notify)
