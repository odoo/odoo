import socket
from urllib.parse import urlsplit

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pk_edi_enable = fields.Boolean(string='Enable E-Invoicing(PK)', help='Enable the Pakistan E-Invoicing features for this company.')
    l10n_pk_edi_first_time_setup = fields.Boolean(string='Enable First Time Setup E-Invoicing(PK)', help='Enable the Pakistan E-Invoicing features for this company.')
    l10n_pk_edi_test_environment = fields.Boolean(string='Test Environment(PK)', groups='base.group_system')
    l10n_pk_edi_test_auth_token = fields.Char(string='E-invoice(PK) Testing Authentication Token', groups='base.group_system')
    l10n_pk_edi_production_auth_token = fields.Char(string='E-invoice(PK) Production Authentication Token', groups='base.group_system')
    l10n_pk_edi_test_vat = fields.Char(string='Registered Test NTN', groups='base.group_system')
    l10n_pk_edi_test_vat_verified = fields.Selection(
        selection=[
            ('not_checked', 'Not Checked'),
            ('registered', 'Registered'),
            ('unregistered', 'Not Registered'),
        ],
        default='not_checked',
        groups='base.group_system',
    )
    l10n_pk_edi_iap_server_ip = fields.Char(string="IP Address", default=lambda self: self._get_iap_server_ip())

    def _get_iap_server_ip(self):
        iap_endpoint = 'https://iap-services.odoo.com'
        if config_endpoint := self.env.ref('l10n_pk_edi.l10n_pk_edi_iap_endpoint', raise_if_not_found=False):
            iap_endpoint = config_endpoint.value
        try:
            hostname = urlsplit(iap_endpoint).hostname
            return socket.gethostbyname(hostname)
        except (socket.gaierror, AttributeError):
            return False

    def _get_l10n_pk_edi_auth_token(self):
        self.ensure_one()
        return self.l10n_pk_edi_test_auth_token if self.l10n_pk_edi_test_environment else self.l10n_pk_edi_production_auth_token

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

        if not self._get_l10n_pk_edi_auth_token():
            token_name = self.env._('Testing') if self.l10n_pk_edi_test_environment else self.env._('Production')
            message = self.env._('Configure the EDI %s Auth Token to enable e-invoicing.') % token_name
            return (
                ('message', message),
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
                if temp_dict['error_code'] != 'l10n_pk_edi_company_auth_key_missing'
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
