from odoo import api, fields, models
from odoo.tools import frozendict


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[('pint_ae', "UAE (Peppol PINT AE)")])
    l10n_ae_company_country_codes = fields.Char(compute='_compute_l10n_ae_company_country_codes')
    l10n_ae_registration_identifier = fields.Char(string='Registration Identifier')
    l10n_ae_registration_identifier_type = fields.Selection([
        ('TL', 'Commercial/Trade license'),
        ('EID', 'Emirates ID'),
        ('PAS', 'Passport'),
        ('CD', 'Cabinet Decision'),
    ], string='Registration Identifier Type')
    l10n_ae_authority_name = fields.Char(
        string='Authority Name',
        help='The authority which has issued the license should be provided',
    )
    l10n_ae_passport_issuing_country_id = fields.Many2one(
        'res.country',
        string='Passport Issuing Country',
        help='Required when Registration Identifier Type is Passport (PAS)',
    )

    @api.depends('company_id', 'country_code')
    @api.depends_context('allowed_company_ids')
    def _compute_l10n_ae_company_country_codes(self):
        for partner in self:
            country_codes = (partner.company_id or self.env.companies).country_id.mapped('code')
            if partner.country_code:
                country_codes.append(partner.country_code)
            partner.l10n_ae_company_country_codes = ",".join(country_codes)

    def _l10n_ae_pint_get_errors(self):
        """ The registration identifier's schemeAgencyName.

        - ibr-010-ae/ibr-012-ae: the passport issuing country for a Passport.
        - ibr-101-ae/ibr-172-ae: the authority name for a Commercial/Trade license.
        """
        self.ensure_one()
        errors = []
        if not self.l10n_ae_registration_identifier:
            return []
        if self.l10n_ae_registration_identifier_type == 'PAS' and not self.l10n_ae_passport_issuing_country_id:
            errors.append(frozendict({
                'message': self.env._("Partner(s) with a Passport registration identifier should have their Passport Issuing Country set."),
                'error_code': 'l10n_ae_pint_partner_passport_issuing_country_missing',
                'level': 'danger',
            }))
        if self.l10n_ae_registration_identifier_type == 'TL' and not self.l10n_ae_authority_name:
            errors.append(frozendict({
                'message': self.env._("Partner(s) with a Commercial/Trade License registration identifier should have their Authority Name set."),
                'error_code': 'l10n_ae_pint_partner_authority_name_missing',
                'level': 'danger',
            }))
        return errors

    def _get_edi_builder(self, invoice_edi_format):
        # EXTENDS 'account_edi_ubl_cii'
        if invoice_edi_format == 'pint_ae':
            return self.env['account.edi.xml.pint_ae']
        return super()._get_edi_builder(invoice_edi_format)

    def _get_ubl_cii_formats_info(self):
        # EXTENDS 'account_edi_ubl_cii'
        formats_info = super()._get_ubl_cii_formats_info()
        formats_info['pint_ae'] = {'countries': ['AE'], 'on_peppol': True}
        return formats_info
