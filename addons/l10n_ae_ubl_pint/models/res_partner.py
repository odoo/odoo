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

    def _group_by_error_code(self):
        self.ensure_one()
        if not self.l10n_ae_registration_identifier:
            return False
        # ibr-010-ae/ibr-012-ae: schemeAgencyName MUST be the passport issuing country code when
        # the registration identifier type is Passport.
        if self.l10n_ae_registration_identifier_type == 'PAS' and not self.l10n_ae_passport_issuing_country_id:
            return (
                ("message", self.env._("Partner(s) with a Passport registration identifier should have their Passport Issuing Country set.")),
                ("error_code", "l10n_ae_ubl_pint_partner_passport_issuing_country_missing"),
                ("level", "danger"),
            )
        # ibr-101-ae/ibr-172-ae: schemeAgencyName MUST be the authority name when the
        # registration identifier type is Commercial/Trade license.
        if self.l10n_ae_registration_identifier_type == 'TL' and not self.l10n_ae_authority_name:
            return (
                ("message", self.env._("Partner(s) with a Commercial/Trade License registration identifier should have their Authority Name set.")),
                ("error_code", "l10n_ae_ubl_pint_partner_authority_name_missing"),
                ("level", "danger"),
            )
        return False

    def _l10n_ae_ubl_pint_export_check(self):
        """Validate Partner for PINT AE compliance."""
        alert_vals = {}
        for error_tuple, invalid_records in self.grouped(lambda m: m._group_by_error_code()).items():
            if not error_tuple:
                continue
            temp_dict = dict(error_tuple)
            alert_vals.update(
                {
                    temp_dict["error_code"]: {
                        "message": temp_dict["message"],
                        "level": temp_dict["level"],
                        "action": invalid_records._get_records_action(),
                        "action_text": self.env._("View Partner(s)"),
                    },
                },
            )
        return alert_vals

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
