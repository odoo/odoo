from odoo import fields, models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'l10n.ae.pint.check.mixin']

    invoice_edi_format = fields.Selection(selection_add=[('pint_ae', "UAE (Peppol PINT AE)")])

    # Legal registration identifier (IBT-030 / IBT-047) and its type (BTAE-15 / BTAE-16).
    l10n_ae_registration_identifier = fields.Char(string='Registration Identifier')
    l10n_ae_registration_identifier_type = fields.Selection([
        ('TL', 'Commercial/Trade license'),
        ('EID', 'Emirates ID'),
        ('PAS', 'Passport'),
        ('CD', 'Cabinet Decision'),
    ], string='Registration Identifier Type')
    # BTAE-12
    l10n_ae_authority_name = fields.Char(
        string='Authority Name',
        help='The authority which has issued the license should be provided',
    )
    # BTAE-18
    l10n_ae_passport_issuing_country_id = fields.Many2one(
        'res.country',
        string='Passport Issuing Country',
        help='Required when Registration Identifier Type is Passport (PAS)',
    )

    def _l10n_ae_pint_group_by_error_code(self):
        """ The registration identifier's schemeAgencyName.

        - ibr-010-ae/ibr-012-ae: the passport issuing country for a Passport.
        - ibr-101-ae/ibr-172-ae: the authority name for a Commercial/Trade license.
        """
        self.ensure_one()
        if not self.l10n_ae_registration_identifier:
            return False
        if self.l10n_ae_registration_identifier_type == 'PAS' and not self.l10n_ae_passport_issuing_country_id:
            return (
                ("message", self.env._("Partner(s) with a Passport registration identifier should have their Passport Issuing Country set.")),
                ("error_code", "l10n_ae_pint_partner_passport_issuing_country_missing"),
                ("level", "danger"),
            )
        if self.l10n_ae_registration_identifier_type == 'TL' and not self.l10n_ae_authority_name:
            return (
                ("message", self.env._("Partner(s) with a Commercial/Trade License registration identifier should have their Authority Name set.")),
                ("error_code", "l10n_ae_pint_partner_authority_name_missing"),
                ("level", "danger"),
            )
        return False

    def _l10n_ae_pint_action_text(self):
        # EXTENDS 'l10n.ae.pint.check.mixin'
        return self.env._("View Partner(s)")

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
