# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api

FINAL_CONSUMER_VAT = '222222222222'  # 'Consumidor Final' is the generic partner used in B2C


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_co_edi_large_taxpayer = fields.Boolean(string='Gran Contribuyente')
    l10n_co_edi_fiscal_regimen = fields.Selection([
        ('48', 'IVA'),
        ('49', 'No Aplica'),
        ('04', 'IC'),
        ('ZA', 'IVA en IC'),
    ], string="Fiscal Regimen", required=True, default='48')
    l10n_co_edi_commercial_name = fields.Char('Commercial Name')
    l10n_co_edi_obligation_type_ids = fields.Many2many('l10n_co_edi.type_code',
                                                       'partner_l10n_co_edi_obligation_types',
                                                       'partner_id', 'type_id',
                                                       string='Obligaciones y Responsabilidades')

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + [
            'l10n_co_edi_fiscal_regimen',
            'l10n_co_edi_obligation_type_ids',
            'l10n_co_edi_large_taxpayer',
            'l10n_co_edi_commercial_name',
        ]

    def _get_vat_without_verification_code(self):
        self.ensure_one()
        # last digit is the verification code, but it could have a - before
        if self.l10n_latam_identification_type_id.l10n_co_document_code != 'rut' or self.vat == FINAL_CONSUMER_VAT:
            return self.vat
        elif self.vat and "-" in self.vat:
            return self.vat.split('-')[0]
        return self.vat[:-1] if self.vat else ''

    def _get_vat_verification_code(self):
        self.ensure_one()
        if self.l10n_latam_identification_type_id.l10n_co_document_code != 'rut':
            return ''
        elif self.vat and "-" in self.vat:
            return self.vat.split('-')[1]
        return self.vat[-1] if self.vat else ''

    def _l10n_co_edi_get_partner_type(self):
        self.ensure_one()
        return '1' if self.is_company else '2'

    def _l10n_co_edi_get_carvajal_code_for_identification_type(self):
        self.ensure_one()
        IDENTIFICATION_TYPE_TO_CARVAJAL_CODE = {
            'rut': '31',
            'id_document': '',
            'id_card': '12',
            'passport': '41',
            'foreign_id_card': '42',
            'external_id': '50',
            'residence_document': '47',
            'PEP': '47',
            'civil_registration': '11',
            'national_citizen_id': '13',
            'niup_id': '91',
            'foreign_colombian_card': '21',
            'foreign_resident_card': '22',
            'diplomatic_card': '',
            'PPT': '48',
            'vat': '50',
        }

        identification_type = self.l10n_latam_identification_type_id.l10n_co_document_code
        return IDENTIFICATION_TYPE_TO_CARVAJAL_CODE[identification_type] if identification_type else ''

    def _l10n_co_edi_get_company_address(self):
        """
        Function forms address of the company avoiding duplicity. contact_address attribute holds the complete address
        of company, which should not be used.
        Information like city, state which is already sent in other tags should be excluded from the company's address.
        """
        self.ensure_one()
        return '%s %s' % (self.street or '', self.street2 or '')

    def _l10n_co_edi_get_fiscal_regimen_code(self):
        if self.l10n_co_edi_fiscal_regimen == '48':
            return '01'
        if self.l10n_co_edi_fiscal_regimen == '49':
            return 'ZZ'
        return self.l10n_co_edi_fiscal_regimen

    def _l10n_co_edi_get_fiscal_regimen_name(self):
        return dict(self._fields["l10n_co_edi_fiscal_regimen"].selection).get(self.l10n_co_edi_fiscal_regimen)
