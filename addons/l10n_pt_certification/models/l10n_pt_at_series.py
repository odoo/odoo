import base64
import logging
import re

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import zeep
from odoo.tools.zeep.exceptions import Fault

from odoo.addons.certificate.tools import CertificateAdapter
from odoo.addons.l10n_pt_certification.const import (
    PT_AT_DOCUMENT_TYPE_MAPPING,
    PT_AT_MEIO_PROCESSAMENTO,
    PT_AT_WS_WSDL_URL,
    PT_CERTIFICATION_NUMBER,
)
from odoo.addons.l10n_pt_certification.utils.series_ws import ATUsernameToken

_logger = logging.getLogger(__name__)

AT_SERIES_ACCOUNTING_DOCUMENT_TYPES = [
    ('out_invoice', 'Invoice (FT)'),
    ('out_receipt', 'Simplified Invoice (FS)'),
    ('out_invoice_receipt', 'Invoice/Receipt (FR)'),
    ('out_refund', 'Credit Note (NC)'),
    ('debit_note', 'Debit Note (ND)'),
    ('payment_receipt', 'Payment Receipt (RG)'),
]


class L10nPtATSeries(models.Model):
    """
    This model allows users to add the AT series created in the Portal das Finanças. An AT Series
    """
    _name = "l10n_pt.at.series"
    _description = "Mapping between Odoo Series and the Official Series for the Autoridade Tributária (AT)"
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of
    _rec_name = 'document_identifier'

    name = fields.Char(
        required=True,
        help="The name of the series will be part of the document number sequence.",
    )
    training_series = fields.Boolean("Training Series")
    date_start = fields.Date("Start Date", required=True, default=fields.Date.today)
    date_end = fields.Date("End Date")
    active = fields.Boolean(compute='_compute_active', search='_search_active')
    company_exclusive_series = fields.Boolean(
        string="Exclusive Series",
        help="If checked, this series will only be used by one company and not shared across branches",
    )
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    journal_id = fields.Many2one(
        'account.journal',
        help="This series will be available for account moves belonging to this, and only this, journal.",
        check_company=True,
        domain="[('type', 'in', ('sale', 'bank', 'credit', 'cash'))]",
    )

    prefix = fields.Char(
        string="Prefix",
        required=True,
        help="The internal code of the document type that will be combined with the Series Name to form "
             "the unique identification of documents.",
    )
    document_type = fields.Selection(
        string="Document Type",
        selection=AT_SERIES_ACCOUNTING_DOCUMENT_TYPES,
        required=True,
        help="Customer Invoices require an Invoice (FT) series, and Sales Receipts require a Simplified Invoice (FS) series.",
    )
    # Used in _rec_name to display the types of documents within an AT Series (displayed in the list view of AT Series)
    document_type_name = fields.Char("Type Name", compute="_compute_document_type_name")
    at_code = fields.Char("AT Validation Code")
    document_identifier = fields.Char(
        "Document Identifier",
        compute='_compute_document_identifier',
        help="The unique identification of documents of this series and type made up of the document type prefix and "
             "the series name, followed by '/' and the number of the document.",
        store=True,
    )

    _type_per_series_uniq = models.Constraint(
        'unique(document_type, name, company_id)',
        "This document type already exists for this series name in this company.",
    )
    _prefix_per_series_uniq = models.Constraint(
        'unique(prefix, name, company_id)',
        "This prefix has already been used in this series name in this company.",
    )
    _at_code_uniq = models.Constraint(
        'unique(at_code)',
        "The AT code must be unique.",
    )

    def _compute_active(self):
        today = fields.Date.today()
        for at_series in self:
            at_series.active = at_series.date_end >= today if at_series.date_end else True

    def _search_active(self, operator, value):
        if value is None:
            return Domain.FALSE
        if isinstance(value, bool):
            value = {value}
        if operator not in ['not in', 'in', '=', '!=']:
            raise ValueError(_('Operator (%s) is not supported', operator))
        today = fields.Date.today()
        active_domain = Domain.OR([
            Domain('date_end', '=', False),
            Domain('date_end', '>=', today),
        ])
        not_active_domain = Domain.AND([
            Domain('date_end', '!=', False),
            Domain('date_end', '<', today),
        ])
        if len(value) == 1:
            if (
                (operator in ['=', 'in'] and True in value)             # active = True or active in [True]
                or (operator in ['!=', 'not in'] and False in value)    # active != False or active not in [False]
            ):
                return active_domain
            if (
                (operator in ['=', 'in'] and False in value)            # active = False or active in [False]
                or (operator in ['!=', 'not in'] and True in value)     # active != True or active not in [True]
            ):
                return not_active_domain

        return Domain.OR([active_domain, not_active_domain])

    def _l10n_pt_is_valid_on(self, date):
        """
        Whether the series' validity window covers ``date``.

        Distinct from ``active``, which asks the narrower question of whether the window is still
        open *today*; the two are routinely required together.
        """
        if not self:
            return False
        self.ensure_one()
        return (
            (not self.date_start or self.date_start <= date)
            and (not self.date_end or self.date_end >= date)
        )

    @api.model
    def _l10n_pt_validity_domain(self, date, prefix=''):
        """
        ``_l10n_pt_is_valid_on`` as a domain, in prefix notation so call sites can spread it.

        ``prefix`` traverses to the series from a related model, e.g. ``'l10n_pt_at_series_id.'``.
        """
        return [
            '|', (f'{prefix}date_start', '=', False), (f'{prefix}date_start', '<=', date),
            '|', (f'{prefix}date_end', '=', False), (f'{prefix}date_end', '>=', date),
        ]

    @api.model
    def _l10n_pt_company_domain(self, company):
        return [
            '|',
            '&', ('company_id', '=', company.id), ('company_exclusive_series', '=', True),
            '&', ('company_id', 'in', company.parent_ids.ids), ('company_exclusive_series', '=', False),
        ]

    @api.depends('document_type')
    def _compute_document_type_name(self):
        """ Used to display the types of document included in an AT Series in the list view """
        for series in self:
            series.document_type_name = dict(series._fields['document_type'].selection).get(series.document_type)

    @api.depends('prefix', 'name')
    def _compute_document_identifier(self):
        """
        Creates the prefix of the document number sequence. Also used to display how the document identifier for records
        under the series will show up in the document.
        Ex: AT Series name = 2025, prefix for invoice documents = FT, document number sequence starts at FT 2025/00001
        """
        for series in self:
            series.document_identifier = ' '.join(filter(None, [series.prefix or '', series.name or '']))

    @api.constrains('name')
    def _check_name(self):
        for series in self:
            if not re.match(r'^[a-zA-Z0-9]+$', series.name):
                raise ValidationError(_(
                    "The name of the series (%s) is invalid. It must consist of only letters and numbers (e.g. 2025, 2025B).",
                    series.name
                ))

    @api.constrains('prefix')
    def _check_prefix(self):
        for series in self:
            if not re.match(r'^[a-zA-Z0-9]+$', series.prefix):
                raise ValidationError(_(
                    "The prefix of the series (%s) is invalid. It must consist of only letters and numbers (e.g. INV, RINV).",
                    series.prefix
                ))

    @api.constrains('document_type', 'journal_id', 'journal_id')
    def _check_journal_requirements(self):
        for series in self:
            if series.document_type == 'payment_receipt' and not series.journal_id:
                raise ValidationError(_("A Payment Journal is required when you have Payment Receipt lines."))
            if series.document_type in {'out_receipt', 'out_invoice', 'out_invoice_receipt', 'out_refund', 'debit_note'} and not series.journal_id:
                raise ValidationError(_("A Sales Journal is required for account move document types (FT, FS, NC, ND)."))

    def _get_at_code(self):
        self.ensure_one()
        if not self.active:
            raise UserError(_("The series %(prefix)s is not active.", prefix=self.prefix))
        return self.at_code

    def _l10n_pt_get_document_number_sequence(self):
        """
        Returns the document number sequence for this AT series (company and document type dependent),
        creating it if needed.
        """
        self.ensure_one()

        sequence_code = f'l10n_pt_certification.{self.document_type}_{self.name.lower()}_sequence'

        if not (sequence := self.env['ir.sequence'].search([
            ('code', '=', sequence_code),
            ('company_id', '=', self.company_id.id),
        ])):
            return self.env['ir.sequence'].create({
                'name': f'{self.document_identifier} Sequence',
                'implementation': 'no_gap',
                'padding': 5,
                'prefix': f'{self.document_identifier}/',
                'company_id': self.company_id.id,
                'code': sequence_code,
            })
        return sequence

    @api.onchange('company_exclusive_series')
    def _onchange_company_exclusive_series(self):
        """ Reset the company_id field when the company_exclusive_series field is unchecked. """
        if not self.company_exclusive_series:
            self.company_id = self.env.company

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.at_code:
                continue
            if not record.company_id.sudo().l10n_pt_at_ws_username:
                continue
            try:
                record.action_register_at_series()
            except Exception:
                _logger.warning(
                    "Failed to auto-register AT series %(name)s (type: %(type)s)",
                    {'name': record.name, 'type': record.document_type},
                    exc_info=True,
                )
        return records

    def write(self, vals):
        protected_fields = {'prefix', 'name', 'document_type', 'date_start', 'date_end', 'training_series', 'journal_id', 'company_exclusive_series', 'company_id'}
        if any(field in vals for field in protected_fields | {'at_code'}):
            for at_series in self:
                if at_series.env['account.move'].search_count([
                    ('l10n_pt_at_series_id', '=', at_series.id),
                    ('state', "in", ('posted', 'cancel')),
                    ('l10n_pt_document_type', '=', at_series.document_type),
                ], limit=1) or at_series.env['account.payment'].search_count([
                    ('l10n_pt_at_series_id', '=', at_series.id),
                    ('state', "in", ('posted', 'cancel')),
                ], limit=1):
                    if any(field in vals for field in protected_fields):
                        raise UserError(_("You cannot change the properties of a series that has already been used by a journal entry."))
                    if 'at_code' in vals and at_series.at_code:
                        raise UserError(_("You cannot change the AT Validation Code of a series that has already been used."))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used(self):
        for at_series in self:
            if (
                self.env['account.move'].search_count([
                    ('l10n_pt_at_series_id', '=', at_series.id),
                    ('state', "in", ('posted', 'cancel')),
                    ('l10n_pt_document_type', '=', at_series.document_type),
                ], limit=1)
                or self.env['account.payment'].search_count([
                    ('l10n_pt_at_series_id', '=', at_series.id),
                    ('state', "in", ('paid', 'canceled')),
                ], limit=1)
            ):
                raise UserError(_("You cannot delete a series that is used. It will automatically be archived after the End Date"))

    def _l10n_pt_at_ws_get_registration_params(self):
        self.ensure_one()
        mapping = PT_AT_DOCUMENT_TYPE_MAPPING.get(self.document_type)
        if not mapping:
            raise UserError(_(
                "Cannot register series of type '%(type)s' with the AT webservice.",
                type=self.document_type
            ))
        return {
            'serie': self.name,
            'tipoSerie': 'F' if self.training_series else 'N',
            'classeDoc': mapping['classeDoc'],
            'tipoDoc': mapping['tipoDoc'],
            'numInicialSeq': 1,
            'dataInicioPrevUtiliz': self.date_start,
            'numCertSWFatur': int(PT_CERTIFICATION_NUMBER),
            'meioProcessamento': PT_AT_MEIO_PROCESSAMENTO,
        }

    def action_register_at_series(self):
        self.ensure_one()
        comp = self.company_id.sudo()

        if comp.l10n_pt_at_ws_env == 'offline':
            return

        if not comp.l10n_pt_at_ws_username or not comp.l10n_pt_at_ws_password:
            raise UserError(_(
                "The AT webservice credentials are not configured for company %(company)s. "
                "Please configure them in the Accounting Settings.",
                company=self.company_id.name,
            ))

        # The AT mandates that the password is RSA-encrypted with their public key. Without the
        # certificate the request cannot be built, and must not fall back to sending the live
        # credential in clear text.
        public_cert = comp.l10n_pt_at_ws_public_cert_id.with_context(bin_size=False)
        if not public_cert.pem_certificate:
            raise UserError(_(
                "The AT public key certificate is not configured for company %(company)s. "
                "It is required to encrypt the password sent to the Autoridade Tributária. "
                "Please configure it in the Accounting Settings.",
                company=self.company_id.name,
            ))
        public_key_pem = base64.b64decode(public_cert.pem_certificate)

        if comp.l10n_pt_at_ws_env == 'test' and not self.training_series:
            self.training_series = True

        wsse_token = ATUsernameToken(
            comp.l10n_pt_at_ws_username,
            comp.l10n_pt_at_ws_password,
            public_key_pem,
        )

        session = requests.Session()
        session.cert = comp.l10n_pt_at_ws_ssl_certificate_id
        session.mount('https://', CertificateAdapter())
        client = comp._get_zeep_client__(
            PT_AT_WS_WSDL_URL,
            wsse=wsse_token,
            session=session,
            settings=zeep.Settings(strict=False),
        )
        service = client.bind('SeriesWSService', 'SeriesWSPort')
        service._binding_options['address'] = comp._l10n_pt_at_ws_get_soap_endpoint()

        params = self._l10n_pt_at_ws_get_registration_params()
        self.at_code = self._registar_serie(service, **params)

    def _registar_serie(self, service, **params):
        try:
            response = service.registarSerie(**params)
        except Fault as e:
            _logger.error('AT SeriesWS registarSerie SOAP fault: %s', e)
            raise UserError(
                _("AT Series registration failed: %(error)s", error=str(e))
            ) from e
        except (OSError, TimeoutError, requests.exceptions.SSLError) as e:
            msg = _("Could not connect to the AT webservice.")
            _logger.error(msg)
            raise UserError(msg) from e

        if not response or not hasattr(response, 'infoResultOper'):
            raise UserError(_("AT Series registration returned an unexpected response."))

        info_result = response.infoResultOper
        if info_result.codResultOper != 2001:
            raise UserError(
                _("AT Series registration error (%(code)s): %(message)s",
                  code=info_result.codResultOper,
                  message=info_result.msgResultOper or '')
            )

        info_serie = response.infoSerie if hasattr(response, 'infoSerie') else None
        if not info_serie or not hasattr(info_serie, 'codValidacaoSerie'):
            raise UserError(_("AT Series registration succeeded but no validation code was returned."))
        return info_serie.codValidacaoSerie

    def get_formview_action(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'l10n_pt_certification.action_open_l10n_pt_at_series_series_list_view'
        )
        action['domain'] = [('journal_id', '=', self.journal_id.id)]
        return action
