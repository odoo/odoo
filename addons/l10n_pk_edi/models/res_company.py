from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pk_edi_enable = fields.Boolean(string='Enable E-Invoicing(PK)', default=True, help='Enable the Pakistan E-Invoicing features for this company.')
    l10n_pk_edi_test_environment = fields.Boolean(string='Test Environment(PK)', default=True, groups='base.group_system')
    l10n_pk_edi_auth_token = fields.Char(string='E-invoice(PK) Auth Token', groups='base.group_system')

    # -------------------------------------------------------------------------
    # Validation Methods
    # -------------------------------------------------------------------------

    def _group_by_error_code(self):
        if not self.vat:
            return (
                ('message', self.env._('Company/ies should have a NTN number.')),
                ('error_code', 'l10n_pk_edi_company_vat_missing'),
                ('level', 'danger'),
            )

        if not self.partner_id._l10n_pk_edi_is_valid_vat():
            return (
                ('message', self.env._('Company/ies has configure invalid NTN/CNIC number.')),
                ('error_code', 'l10n_pk_edi_company_vat_invalid'),
                ('level', 'danger'),
            )

        if not all(self[field] for field in ('street', 'city', 'state_id', 'country_id')):
            return (
                ('message', self.env._('Company/ies should have a complete address, verify their Street, City, State and Country.')),
                ('error_code', 'l10n_pk_edi_company_address_missing'),
                ('level', 'danger'),
            )

        if not self.l10n_pk_edi_auth_token:
            return (
                ('message', self.env._('Configure the EDI Auth Token to enable e-invoicing.')),
                ('error_code', 'l10n_pk_edi_company_auth_key_missing'),
                ('level', 'danger'),
            )
        return False

    def _l10n_pk_edi_export_check(self):
        alert_vals = {}
        for error_tuple, invalid_records in self.grouped(lambda m: m._group_by_error_code()).items():
            if not error_tuple:
                continue
            temp_dict = dict(error_tuple)
            invalid_records_action = (
                invalid_records._get_records_action()
                if temp_dict['error_code'] != 'company_auth_key_missing'
                else self.env['res.config.settings']._get_records_action(context={**self.env.context, 'module': 'account'})
            )
            alert_vals.update({
                temp_dict['error_code']: {
                    'message': temp_dict['message'],
                    'level': temp_dict['level'],
                    'action': invalid_records_action,
                    'action_text':  self.env._('View Company/ies'),
                },
            })
        return alert_vals
