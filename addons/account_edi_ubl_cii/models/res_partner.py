# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.addons.account.models.company import PEPPOL_DEFAULT_COUNTRIES


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(
        selection_add=[
            ('facturx', "France (FacturX)"),
            ('ubl_bis3', "EU Standard (Peppol Bis 3.0)"),
            ('xrechnung', "Germany (XRechnung)"),
            ('nlcius', "Netherlands (NLCIUS)"),
            ('ubl_a_nz', "Australia BIS Billing 3.0 A-NZ"),
            ('ubl_sg', "Singapore BIS Billing 3.0 SG"),
        ],
    )
    is_ubl_format = fields.Boolean(compute='_compute_is_ubl_format')
    endpoint_ids = fields.One2many(
        comodel_name='res.partner.identification',
        compute='_compute_endpoint_ids',
    )

    @api.depends('identifier_ids')
    def _compute_endpoint_ids(self):
        for partner in self:
            partner.endpoint_ids = partner.identifier_ids.filtered(lambda i: i.is_ubl_cii)

    def _get_main_endpoint(self):
        self.ensure_one()
        # Any endpoint (an identifier with code that is an EAS) works.
        return self.endpoint_ids[:1]

    @api.model
    def _get_ubl_cii_formats(self):
        return list(self._get_ubl_cii_formats_info().keys())

    @api.model
    def _get_ubl_cii_formats_info(self):
        return {
            'ubl_bis3': {'countries': list(PEPPOL_DEFAULT_COUNTRIES), 'on_peppol': True, 'sequence': 200},
            'xrechnung': {'countries': ['DE'], 'on_peppol': True},
            'ubl_a_nz': {'countries': ['NZ', 'AU'], 'on_peppol': False},  # Not yet available through Odoo's Access Point, although it's a Peppol valid format
            'nlcius': {'countries': ['NL'], 'on_peppol': True},
            'ubl_sg': {'countries': ['SG'], 'on_peppol': False},  # Same.
            'facturx': {'countries': ['FR'], 'on_peppol': False},
        }

    @api.model
    def _get_ubl_cii_formats_by_country(self):
        formats_info = self._get_ubl_cii_formats_info()
        countries = {country for format_val in formats_info.values() for country in (format_val.get('countries') or [])}
        return {
            country_code: [
                format_key
                for format_key, format_val in formats_info.items() if country_code in (format_val.get('countries') or [])
            ]
            for country_code in countries
        }

    def _get_suggested_ubl_cii_edi_format(self):
        self.ensure_one()
        format_mapping = self._get_ubl_cii_formats_by_country()
        country_code = self.commercial_partner_id._deduce_country_code()
        if country_code in format_mapping:
            formats_by_country = format_mapping[country_code]
            # return the format with the smallest sequence
            if len(formats_by_country) == 1:
                return formats_by_country[0]
            else:
                formats_info = self._get_ubl_cii_formats_info()
                return min(formats_by_country, key=lambda e: formats_info[e].get('sequence', 100))  # we use a sequence of 100 by default
        return False

    def _get_suggested_peppol_edi_format(self):
        self.ensure_one()
        suggested_format = self.commercial_partner_id._get_suggested_ubl_cii_edi_format()
        return suggested_format if suggested_format in self.env['res.partner']._get_peppol_formats() else 'ubl_bis3'

    def _get_peppol_edi_format(self):
        self.ensure_one()
        return self.invoice_edi_format or self._get_suggested_peppol_edi_format()

    @api.model
    def _get_peppol_formats(self):
        formats_info = self._get_ubl_cii_formats_info()
        return [format_key for format_key, format_vals in formats_info.items() if format_vals.get('on_peppol')]

    @api.depends_context('company')
    @api.depends('invoice_edi_format')
    def _compute_is_ubl_format(self):
        for partner in self:
            partner.is_ubl_format = partner.invoice_edi_format in self._get_ubl_cii_formats()

    @api.model
    def _get_edi_builder(self, invoice_edi_format):
        if invoice_edi_format == 'xrechnung':
            return self.env['account.edi.xml.ubl_de']
        if invoice_edi_format == 'facturx':
            return self.env['account.edi.xml.cii']
        if invoice_edi_format == 'ubl_a_nz':
            return self.env['account.edi.xml.ubl_a_nz']
        if invoice_edi_format == 'nlcius':
            return self.env['account.edi.xml.ubl_nl']
        if invoice_edi_format == 'ubl_bis3':
            return self.env['account.edi.xml.ubl_bis3']
        if invoice_edi_format == 'ubl_sg':
            return self.env['account.edi.xml.ubl_sg']
