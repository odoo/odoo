# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[('pint_ae', "UAE (Peppol PINT AE)")])
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
