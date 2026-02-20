from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # -------------------------------------------------------------------------
    # Fields
    # -------------------------------------------------------------------------

    l10n_pk_edi_enable = fields.Boolean(
        string="Enable E-Invoicing(PK)",
        default=True,
        help="Enable the Pakistan E-Invoicing features for this company.",
    )
    l10n_pk_edi_test_environment = fields.Boolean(
        string="Test Environment(PK)",
        default=True,
        groups='base.group_system',
    )
    l10n_pk_edi_auth_token = fields.Char(
        string="E-invoice(PK) Auth Token",
        groups='base.group_system',
    )

    # -------------------------------------------------------------------------
    # Validation Methods
    # -------------------------------------------------------------------------

    def _l10n_pk_edi_export_check(self):
        """Validate companies for E-Invoicing compliance."""

        def _group_by_error_code(company):
            if not company.vat:
                return 'company_vat_missing'
            elif not company.partner_id._l10n_pk_edi_is_valid_vat():
                return 'company_vat_invalid'
            elif not all(company[field] for field in ('street', 'city', 'state_id', 'country_id')):
                return 'company_address_missing'
            elif not company.l10n_pk_edi_auth_token:
                return 'company_auth_key_missing'
            return False

        error_messages = {
            'company_vat_missing': self.env._(
                "Company/ies should have a NTN number."
            ),
            'company_vat_invalid': self.env._(
                "Company/ies has configure invalid NTN/CNIC number."
            ),
            'company_address_missing': self.env._(
                "Company/ies should have a complete address, verify their Street, City, State and Country."
            ),
            'company_auth_key_missing': self.env._(
                "Configure the EDI Auth Token to enable e-invoicing."
            ),
        }

        alerts = {}
        for error_code, invalid_record in self.grouped(_group_by_error_code).items():
            if not error_code:
                continue

            alerts[f'l10n_pk_edi_{error_code}'] = {
                'level': 'danger',
                'message': error_messages[error_code],
                'action_text': self.env._(
                    "View %s", error_code != 'company_auth_key_missing' and "Company/ies" or "Configuration"
                ),
                'action': (
                    error_code != 'company_auth_key_missing'
                    and invalid_record._get_records_action(name=self.env._("Check Company/ies"))
                    or self.env['res.config.settings']._get_records_action(
                        context={**self.env.context, 'module': 'account'}
                    )
                ),
            }

        return alerts
