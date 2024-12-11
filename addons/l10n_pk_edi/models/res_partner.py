# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # -------------------------------------------------------------------------
    # Validation Methods
    # -------------------------------------------------------------------------

    def _l10n_pk_edi_export_check(self, checks=None):
        checks = checks or ['partner_state_missing']
        fields_to_check = {
            'partner_vat_missing': {
                'fields': [('vat',)],
                'message': _("Partner(s) should have a NTN number."),
            },
            'partner_vat_invalid': {
                'fields': [('vat',)],
                'message': _("Partner(s) has invalid NTN Number. It must consist of exactly 7 digits."),
            },
            'partner_state_missing': {
                'fields': [('state_id',), ('country_id',)],
                'message': _("Partner(s) should have a State and Country."),
            },
            'partner_full_address_missing': {
                'fields': [('street', 'street2'), ('state_id',), ('city',), ('country_id',)],
                'message': _("Partner(s) should have a complete address, verify their Street, City, State and Country."),
            },
        }
        selected_checks = {k: v for k, v in fields_to_check.items() if k in checks}
        errors = {}
        for key, check in selected_checks.items():
            for fields_tuple in check['fields']:
                if key == 'partner_vat_invalid':
                    invalid_records = self.filtered(lambda record: record.vat and len(record.vat) != 7)
                else :
                    invalid_records = self.filtered(
                        lambda record: not any(record[field] for field in fields_tuple)
                    )
                if invalid_records:
                    errors[f'l10n_pk_edi_{key}'] = {
                        'level': 'danger',
                        'message': check['message'],
                        'action_text': _("View Partner(s)"),
                        'action': invalid_records._get_records_action(name=_("Check Partner(s)")),
                    }
        return errors
