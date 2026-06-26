import re
import logging

from odoo import api, fields, models

from odoo.exceptions import UserError
from odoo.tools.sql import SQL

from odoo.addons.iap.tools import iap_tools
from odoo.addons.l10n_fr_pdp.tools.demo_utils import handle_demo

PDP_identifier_re = re.compile(r'^([0-9]{9})(_[0-9]{14})?(_.+)?$')

_logger = logging.getLogger(__name__)

ENDPOINT = 'https://pdp.odoo.com'
TEST_ENDPOINT = 'https://pdp.test.odoo.com'


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_pdp_send_to_ppf = fields.Boolean(
        string="Send to PPF",
        help="Activate Flux 1 regulatory data, Flux 6 mandatory statuses and Flux 10 e-reporting generation for this company.",
        default=True,
        groups='base.group_user',
    )
    l10n_fr_pdp_pilot_phase = fields.Boolean(
        string="E-Invoicing Pilot Phase",
        help="Participate in the Pilot Phase of the French E-Invoicing. This way you are able to test it before it becomes mandatory.",
        groups='base.group_user',
    )
    l10n_fr_pdp_annuaire_start_date = fields.Date(
        string="Annuaire Start Date",
        help="The date on which the company is registered on the annuaire for the French e-invoicing.",
        groups='base.group_user',
    )
    l10n_fr_pdp_registered = fields.Boolean(
        string="Approved Platform Registerd",
        compute="_compute_l10n_fr_pdp_registered",
        groups='base.group_user',
    )
    pdp_identifier = fields.Char(
        compute='_compute_pdp_identifier',
        inverse='_inverse_pdp_identifier',
        groups='base.group_user',
    )
    l10n_fr_pdp_periodicity = fields.Selection(  # TODO prevent changing if flows exist ?
        selection=[
            ('normal_monthly', "Real Monthly Normal Regime"),
            ('normal_quarterly', "Real Normal Quarterly Regime"),
            ('simplified_monthly', "Simplified VAT Regime (Monthly)"),
            ('simplified_bimonthly', "Franchised VAT Regime (Bimonthly)"),
        ],
        string="Flow 10 Report Periodicity",
        default='normal_monthly',
        required=True,
        help="""Legal reporting period for transaction and payments flows according to the TVA regime table.
        Real Monthly Normal Regime : transactions reported by decade, payments reported monthly
        Real Normal Quarterly Regime : transactions reported monthly, payments reported monthly
        Simplified VAT Regime (Monthly) : transactions reported monthly, payments reported monthly
        Franchised VAT Regime (Bimonthly) : transactions reported bimonthly, payments reported bimonthly
        """,
        groups='base.group_user',
    )
    l10n_fr_f10_enable_reporting = fields.Boolean(
        string="Enable Flux 10 Reporting",
        compute='_compute_l10n_fr_f10_enable_reporting',
        store=True,
        readonly=True,
        groups='base.group_user',
    )
    l10n_fr_pdp_flow_10_start_date = fields.Date(
        compute='_compute_l10n_fr_pdp_flow_10_start_date',
        groups='base.group_user',
    )
    pdp_kyc_status = fields.Selection(
        selection=[
            ('processing', "Processing"),
            ('success', "Success"),
            ('fail', "Fail"),
        ],
        groups='base.group_user',
    )
    pdp_authentication_uuid = fields.Char(
        string="Authentication IAP UUID",
        groups='account.group_account_invoice',
    )

    @api.depends('peppol_eas', 'peppol_endpoint')
    def _compute_pdp_identifier(self):
        for record in self:
            partner = record.partner_id
            record.pdp_identifier = partner.peppol_endpoint if partner.peppol_eas == '0225' else False

    def _inverse_pdp_identifier(self):
        for record in self:
            if not record.pdp_identifier:
                continue
            match = PDP_identifier_re.match(record.pdp_identifier or '')
            siren = match and match.group(1)
            if not siren:
                raise UserError(self.env._("The identifier %s is not valid. The expected format is: SIREN, SIREN_SIRET, SIREN_SIRET_CodeRoutage or SIREN_SuffixeAdressage", record.pdp_identifier))
            siret = match.group(2)[1:] if match and match.group(2) else False  # Remove `_` at the start
            record.partner_id.write({
                'peppol_eas': '0225',
                'peppol_endpoint': record.pdp_identifier,  # Will be verified by `_check_peppol_fields` constraint
                'company_registry': siret or siren,
            })

    @api.depends('l10n_fr_pdp_annuaire_start_date', 'account_peppol_proxy_state')
    def _compute_l10n_fr_pdp_registered(self):
        for company in self:
            company.l10n_fr_pdp_registered = (
                company.account_peppol_proxy_state == 'receiver'
                and company.l10n_fr_pdp_annuaire_start_date
                and company.l10n_fr_pdp_annuaire_start_date <= fields.Date.context_today(self)
            )

    def _force_update_l10n_fr_f10_moves(self):
        companies = self.filtered(lambda company: company.l10n_fr_f10_enable_reporting)
        if not companies:
            return
        account_ids = self.env['account.account'].search([
            ('account_type', 'in', ['asset_receivable', 'liability_payable']),
            ('company_ids', 'in', companies.ids),
        ]).ids
        date_company_conditions = SQL(
            '(%s)',
            SQL(' OR ').join(SQL(
                '(move.date >= %(date)s AND move.company_id = %(company_id)s)',
                date=company._pdp_get_flow_10_start_date(),
                company_id=company.id,
            ) for company in companies),
        )
        res = self.env.execute_query(
            self._l10n_fr_pdp_get_f10_moves_query(tuple(account_ids), date_company_conditions),
        )
        moves = self.env['account.move'].browse(move_id for move_id, in res)
        moves._compute_l10n_fr_pdp_flow_10_operation_type()
        moves._compute_l10n_fr_pdp_flow_10_report_type()

    def _l10n_fr_pdp_get_f10_moves_query(self, account_ids, date_company_conditions):
        return SQL('''
            -- payments --
            SELECT move.id
              FROM account_move move
              JOIN account_move_line reco_aml ON reco_aml.move_id = move.id AND reco_aml.account_id IN %(account_ids)s
              JOIN account_partial_reconcile apr ON apr.debit_move_id = reco_aml.id OR apr.credit_move_id = reco_aml.id
             WHERE move.move_type = 'entry'
               AND %(date_company_conditions)s
               AND move.state = 'posted'

             UNION

            -- transactions --
            SELECT move.id
              FROM account_move move
             WHERE move.move_type IN ('out_invoice', 'out_refund', 'out_receipt', 'in_invoice', 'in_refund')  -- not in_receipt !
               AND %(date_company_conditions)s
               AND move.state = 'posted'
                ''',
                account_ids=account_ids,
                date_company_conditions=date_company_conditions,
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

    def _peppol_allows_document_reception(self):
        self.ensure_one()
        return super()._peppol_allows_document_reception() and self.country_code != 'FR'

    @handle_demo
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

    def _pdp_get_flow_10_start_date(self):
        self.ensure_one()
        if (param_start_date := self.env['ir.config_parameter'].sudo().get_param(
            f'l10n_fr_pdp.flow10.start.date.{self.id}',
        )):
            period_data = self.env['l10n.fr.pdp.reports.flow']._get_period_flow_properties(
                self,
                fields.Date.from_string(param_start_date),
                'payment',
            )
            return period_data['period_start']
        return self.l10n_fr_pdp_flow_10_start_date

    @api.depends('l10n_fr_pdp_annuaire_start_date', 'l10n_fr_pdp_periodicity')
    def _compute_l10n_fr_pdp_flow_10_start_date(self):
        changed_companies = self.browse()
        for company in self:
            previous_date = company.l10n_fr_pdp_flow_10_start_date
            if company.l10n_fr_pdp_annuaire_start_date:
                period_data = self.env['l10n.fr.pdp.reports.flow']._get_period_flow_properties(
                    company,
                    company.l10n_fr_pdp_annuaire_start_date,
                    'payment',
                )
                company.l10n_fr_pdp_flow_10_start_date = period_data['period_start']
            else:
                company.l10n_fr_pdp_flow_10_start_date = None
            if previous_date != company.l10n_fr_pdp_flow_10_start_date:
                changed_companies += company
        changed_companies._force_update_l10n_fr_f10_moves()

    @api.depends('l10n_fr_pdp_send_to_ppf', 'account_fiscal_country_id', 'account_peppol_edi_user', 'l10n_fr_pdp_pilot_phase')
    def _compute_l10n_fr_f10_enable_reporting(self):
        changed_companies = self.browse()
        for company in self:
            previous_state = company.l10n_fr_f10_enable_reporting
            company.l10n_fr_f10_enable_reporting = (
                company.l10n_fr_pdp_send_to_ppf
                and company.l10n_fr_pdp_pilot_phase
                and company.account_peppol_edi_user
                and company.account_fiscal_country_id.code == 'FR'
                and company.currency_id == self.env.ref('base.EUR')
            )
            if not previous_state and company.l10n_fr_f10_enable_reporting:
                changed_companies += company
        changed_companies._force_update_l10n_fr_f10_moves()

    def _pdp_get_iap_url(self):
        self.ensure_one()
        return ENDPOINT if self._get_peppol_edi_mode() == 'prod' else TEST_ENDPOINT

    def _refresh_pdp_authentication_status(self, send_bus=True):
        self.ensure_one()
        base_url = self._pdp_get_iap_url()
        response = iap_tools.iap_jsonrpc(f'{base_url}/api/signaturit_id_authentication/1/kyc_status', params={
            'object_uuid': self.pdp_authentication_uuid,
        })
        kyc_status = response.get('kyc_status')
        if kyc_status in {'success', 'fail'}:
            self.pdp_kyc_status = kyc_status
            if self.env['account.move']._can_commit():
                self.env.cr.commit()
            if not send_bus:  # If called manually from the wizard we do not need the JS to handle it
                return
            # We are getting the last registration wizard creator to send him the notification.
            # If we don't have any wizard, the user will get the new screen when he will continue the flow.
            pdp_registration = self.env['pdp.registration'].search([('pdp_authentication_uuid', '=', self.pdp_authentication_uuid)], order='id DESC', limit=1)
            if user := pdp_registration.create_uid:
                user._bus_send(
                    'auth_done',
                    {'pdp_registration_id': pdp_registration.id},
                )
