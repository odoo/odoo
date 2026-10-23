import re

from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # -------------------------------------------------------------------------
    # Validation Methods
    # -------------------------------------------------------------------------

    def _l10n_pk_edi_is_valid_vat(self):
        """
        Check whether the partner VAT (NTN/CNIC) is valid for Pakistan E-Invoicing.

        Supported formats:
            - NTN: 12345-1234567-1
            - NTN (legacy): 1234567, 12345678, 1234567-8
            - CNIC: 12345-1234567-1

        Returns:
            bool: True if VAT exists and matches a valid PK format, otherwise False.
        """

        self.ensure_one()

        if not self.vat:
            return False

        pk_vat_pattern = re.compile(r'^(\d{5}-\d{7}-\d{1}|\d{7,8}|\d{7}-\d{1})$')
        return bool(pk_vat_pattern.match(self.vat))

    def _l10n_pk_edi_export_check(self):
        """Validate partners for E-Invoicing compliance."""

        def _group_by_error_code(partner):
            if not all(partner[field] for field in (
                'street', 'city', 'zip', 'state_id', 'country_id'
            )):
                return 'partner_address_missing'
            return False

        error_messages = {
            'partner_address_missing': self.env._(
                "Partner(s) should have a complete address,"
                "verify their Street, City, ZIP, State and Country."
            ),
        }

        alerts = {}
        for error_code, invalid_record in self.grouped(_group_by_error_code).items():
            if not error_code:
                continue

            alerts[f'l10n_pk_edi_{error_code}'] = {
                'level': 'danger',
                'message': error_messages[error_code],
                'action_text': self.env._("View Partner(s)"),
                'action': invalid_record._get_records_action(name=self.env._("Check Partner(s)")),
            }

        return alerts
