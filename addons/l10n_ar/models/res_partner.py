# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.partner_identifiers import TIN_CATEGORIES, is_identifier_void
import stdnum.ar
import re
import logging

from odoo.addons.l10n_ar.tools.partner_identifiers import (
    AR_ADDITIONAL_IDENTIFIERS_METADATA,
    AR_AFIP_CODES,
    AR_CUIT_AFIP_CODE,
    AR_FOREIGN_ID_AFIP_CODE,
    AR_STATE_TO_CI_AFIP_CODE,
)

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_ar_formatted_vat = fields.Char(
        compute='_compute_l10n_ar_formatted_vat', string="Formatted VAT", help='Computed field that will convert the'
        ' CUIT to the format {person_category:2}-{number:10}-{validation_number:1}')

    l10n_ar_gross_income_number = fields.Char('Gross Income Number')
    l10n_ar_gross_income_type = fields.Selection(
        [('multilateral', 'Multilateral'), ('local', 'Local'), ('exempt', 'Exempt')],
        'Gross Income Type', help='Argentina: Type of gross income: exempt, local, multilateral.')
    l10n_ar_afip_responsibility_type_id = fields.Many2one(
        'l10n_ar.afip.responsibility.type', string='ARCA Responsibility Type', index='btree_not_null', help='Defined by ARCA to'
        ' identify the type of responsibilities that a person or a legal entity could have and that impacts in the'
        ' type of operations and requirements they need.')
    l10n_ar_afip_code = fields.Char(
        string='AFIP Identification Code',
        compute='_compute_l10n_ar_afip_identification', store=True,
        help='AFIP catalog code (catálogo A4) derived from the partner identifiers.',
    )
    l10n_ar_afip_id_value = fields.Char(
        string='AFIP Identification Number',
        compute='_compute_l10n_ar_afip_identification', store=True,
        help='Identification number reported to AFIP.',
    )

    @api.depends('vat', 'additional_identifiers', 'state_id', 'commercial_partner_id.country_id',
                 'commercial_partner_id.vat', 'commercial_partner_id.additional_identifiers')
    def _compute_l10n_ar_afip_identification(self):
        """ The identification the partner is invoiced with, its preferred identifier paired
        with the AFIP code describing which document it is."""
        for partner in self:
            vals = partner._get_preferred_legal_entity_identifier_vals()
            if not vals:
                afip_code = None
            elif vals['key'] == 'AR_CI':
                afip_code = AR_STATE_TO_CI_AFIP_CODE.get(partner.state_id.code)
            else:
                is_cuit = 'AR' in (vals.get('countries') or []) and vals.get('category') in TIN_CATEGORIES
                afip_code = AR_AFIP_CODES.get(vals['key']) or (AR_CUIT_AFIP_CODE if is_cuit else AR_FOREIGN_ID_AFIP_CODE)
            partner.l10n_ar_afip_code = afip_code
            partner.l10n_ar_afip_id_value = vals.get('value')

    @api.depends('vat', 'l10n_ar_afip_code')
    def _compute_l10n_ar_formatted_vat(self):
        """ This will add some dash to the CUIT number (VAT AR) in order to show in his natural format:
        {person_category}-{number}-{validation_number} """
        recs_cuit = self.filtered(lambda p: p.l10n_ar_afip_code == AR_CUIT_AFIP_CODE and p.vat)
        for rec in recs_cuit:
            try:
                rec.l10n_ar_formatted_vat = stdnum.ar.cuit.format(rec.vat)
            except Exception as error:
                rec.l10n_ar_formatted_vat = rec.vat
                _logger.runbot("Argentinean VAT was not formatted: %s", repr(error))
        remaining = self - recs_cuit
        remaining.l10n_ar_formatted_vat = False

    @api.depends('vat', 'commercial_partner_id', 'country_id', 'l10n_ar_afip_code')
    def _compute_is_company(self):
        "True if partner is considered a company in Argentina, based on Identification Type and CUIT prefix."
        l10n_ar_partners = self.filtered(
            lambda p: not is_identifier_void(p.vat)
                and p.l10n_ar_afip_code
                and p.country_code == 'AR'
        )
        for partner in l10n_ar_partners:
            afip_code = partner.l10n_ar_afip_code
            prefix = (partner.vat or '')[:2]

            if (
                afip_code == AR_CUIT_AFIP_CODE and prefix in ('30', '33', '34', '51', '55')  # CUIT
                and partner.commercial_partner_id == partner
            ):
                partner.is_company = True
            else:
                partner.is_company = False  # CUIL or DNI or Unknown type → default to individual

        super(ResPartner, self - l10n_ar_partners)._compute_is_company()

    @api.constrains('additional_identifiers', 'state_id')
    def _check_l10n_ar_state(self):
        """ The generic state ID (`AR_CI`) derives its AFIP document type from the
        partner's state."""
        for partner in self:
            if partner._get_additional_identifier('AR_CI') and not AR_STATE_TO_CI_AFIP_CODE.get(partner.state_id.code):
                raise ValidationError(self.env._(
                    "The state ID (CI) requires an Argentine state on the address to determine"
                    " its document type. Please set a state that issues a state ID (Buenos Aires,"
                    " Córdoba, …)",
                ))

    @api.model
    def _get_all_additional_identifiers_metadata(self):
        return {**super()._get_all_additional_identifiers_metadata(), **AR_ADDITIONAL_IDENTIFIERS_METADATA}

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_ar_afip_responsibility_type_id']

    def ensure_vat(self):
        """ This method is a helper that returns the VAT number is this one is defined if not raise an UserError.

        VAT is not mandatory field but for some Argentinean operations the VAT is required, for eg  validate an
        electronic invoice, build a report, etc.

        This method can be used to validate is the VAT is proper defined in the partner """
        self.ensure_one()
        if self.l10n_ar_afip_code != AR_CUIT_AFIP_CODE or not self.vat:
            raise UserError(_('No VAT configured for partner [%i] %s', self.id, self.name))
        return self.vat

    def _get_frontend_writable_fields(self):
        frontend_writable_fields = super()._get_frontend_writable_fields()
        frontend_writable_fields.add('l10n_ar_afip_responsibility_type_id')

        return frontend_writable_fields

    def _get_mandatory_billing_address_fields(self, country_sudo, **kwargs):
        mandatory_fields = super()._get_mandatory_billing_address_fields(country_sudo, **kwargs)
        if self.env.company.country_code == 'AR':
            mandatory_fields.add('l10n_ar_afip_responsibility_type_id')
        return mandatory_fields

    def _get_id_number_sanitize(self):
        """ Sanitize the identification number: drop its separators and return it as an integer,
        or as its alphanumeric value when it is not only made of digits (e.g. a passport).
        Returns 0 when no identifier is set, the number ARCA expects for an anonymous consumer."""
        self.ensure_one()
        vals = self._get_preferred_legal_entity_identifier_vals()
        if not vals:
            return 0
        normalized = self._validate_identifier(vals['key'], vals['value'])['value'] or ''
        sanitized = re.sub(r'[^0-9a-zA-Z]', '', normalized)
        return int(sanitized) if sanitized.isdigit() else sanitized
