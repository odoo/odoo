# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # -------------------------------------------------------------------------
    # Validation Methods
    # -------------------------------------------------------------------------

    def _l10n_pk_edi_export_check(self):
        """
            Validating Partner for E-Invoicing Compliance
        """

        def _group_by_error_code(partner):
            if not partner.vat:
                return 'partner_vat_missing'
            if partner.country_code == 'PK' and len(partner.vat) != 7:
                return 'partner_vat_invalid'
            if not all(partner[field] for field in ('street', 'city', 'state_id', 'country_id')):
                return 'partner_full_address_missing'
            return False

        error_messages = {
            'partner_state_missing': _(
                "Partner(s) should have a State and Country."
            ),
            'partner_vat_missing': _(
                "Partner(s) should have a NTN number."
            ),
            'partner_vat_invalid': _(
                "Partner(s) has invalid NTN Number. It must consist of exactly 7 digits."
            ),
            'partner_full_address_missing': _(
                "Partner(s) should have a complete address, verify their Street, City, State and Country."
            ),
        }
        return {
            f"l10n_pk_edi_{error_code}": {
                'level': 'danger',
                'message': error_messages[error_code],
                'action_text': _("View Partner(s)"),
                'action': partners._get_records_action(name=_("Check Partner(s)")),
            } for error_code, partners in self.grouped(_group_by_error_code).items() if error_code
        }
