# -*- coding: utf-8 -*-

from odoo import models, fields, _, api
from odoo.addons.iap import jsonrpc
from odoo.exceptions import ValidationError, UserError
import requests
from requests.exceptions import ConnectTimeout
from urllib.parse import urljoin

DEFAULT_ENDPOINT = 'https://l10n-de-pos.api.odoo.com/api/l10n_de_pos'


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_de_fiskaly_api_key = fields.Char(string="Fiskaly API Key", groups="base.group_erp_manager")
    l10n_de_fiskaly_api_secret = fields.Char(string="Fiskaly API Secret", groups="base.group_erp_manager")
    l10n_de_fiskaly_organization_id = fields.Char(string="Fiskaly Organization ID")
    is_country_germany = fields.Boolean(string="Company located in Germany", compute='_compute_is_country_germany')
    l10n_de_fiskaly_kassensichv_token = fields.Char(string="Fiskaly Kassensichv Token", groups="base.group_erp_manager", help="Store the temporary token used for the Kassensichv API")
    l10n_de_fiskaly_dsfinvk_token = fields.Char(string="Fiskaly DSFinV-K Token", groups="base.group_erp_manager", help="Store the temporary token used for the DSFinV-K API")

    @api.depends('country_id')
    def _compute_is_country_germany(self):
        for company in self:
            company.is_country_germany = company.country_id.code == 'DE'

    def write(self, values):
        res = super().write(values)
        for company in self:
            if company.l10n_de_is_germany_and_fiskaly():
                on_change_fields = ['name', 'street', 'street2', 'zip', 'city', 'vat', 'l10n_de_stnr',
                                    'l10n_de_widnr']
                if set(on_change_fields) & set(values):
                    params = company._l10n_de_create_organization_payload()
                    self._l10n_de_fiskaly_iap_rpc('/update', params=params)
        return res

    def l10n_de_is_germany_and_fiskaly(self):
        return self.is_country_germany and self.l10n_de_fiskaly_organization_id

    @api.model
    def _l10n_de_fiskaly_kassensichv_url(self):
        return self.env['ir.config_parameter'].sudo().get_param('l10n_de_fiskaly_kassensichv_url', 'https://kassensichv-middleware.fiskaly.com')

    @api.model
    def _l10n_de_fiskaly_dsfinvk_api_url(self):
        return self.env['ir.config_parameter'].sudo().get_param('l10n_de_fiskaly_dsfinvk_url', 'https://dsfinvk.fiskaly.com')

    def _l10n_de_fiskaly_kassensichv_auth(self, version):
        """
        Return the url and headers containing the token to use the Kassensichv API.
        """
        url = urljoin(self._l10n_de_fiskaly_kassensichv_url(), '/api/v%s' % version)
        if not self.sudo().l10n_de_fiskaly_kassensichv_token:
            auth_response = requests.post(url + '/auth', json={
                'api_secret': self.sudo().l10n_de_fiskaly_api_secret,
                'api_key': self.sudo().l10n_de_fiskaly_api_key
            }, timeout=300)
            if auth_response.status_code == 401:
                raise ValidationError(_("The combination of your Fiskaly API key and secret is incorrect. " \
                                        "Please update them in your company settings"))
            self.sudo().l10n_de_fiskaly_kassensichv_token = auth_response.json()['access_token']
        headers = {'Authorization': 'Bearer ' + self.sudo().l10n_de_fiskaly_kassensichv_token}
        return url, headers

    def _l10n_de_fiskaly_kassensichv_rpc(self, method, path, json=None, version=2, recursive=False):
        try:
            timeout = 300
            url, headers = self._l10n_de_fiskaly_kassensichv_auth(version)
            if method == 'GET':
                res = requests.get(url + path, headers=headers, timeout=timeout)
            elif method == 'POST':
                res = requests.post(url + path, headers=headers, json=json, timeout=timeout)
            elif method == 'PUT':
                res = requests.put(url + path, headers=headers, json=json, timeout=timeout)
            elif method == 'PATCH':
                res = requests.patch(url + path, headers=headers, json=json, timeout=timeout)
            else:
                raise UserError(_('Invalid method'))
            if res.status_code == 401 and not recursive:
                self.sudo().l10n_de_fiskaly_kassensichv_token = None
                res = self._l10n_de_fiskaly_kassensichv_rpc(method, path, json, version, True)
            res.raise_for_status()
            return res
        except ConnectionError:
            raise UserError(_("Connection lost between Odoo and Fiskaly."))
        except ConnectTimeout:
            raise UserError(_("There are some connection issues between us and Fiskaly, try again later."))

    def _l10n_de_fiskaly_dsfinvk_auth(self, version):
        """
        Return the url and headers containing the token to use the DSFinV-K API.
        """
        url = urljoin(self._l10n_de_fiskaly_dsfinvk_api_url(), '/api/v%s' % version)
        if not self.sudo().l10n_de_fiskaly_dsfinvk_token:
            auth_response = requests.post(url + '/auth', json={
                'api_secret': self.sudo().l10n_de_fiskaly_api_secret,
                'api_key': self.sudo().l10n_de_fiskaly_api_key
            }, timeout=300)
            if auth_response.status_code == 401:
                raise ValidationError(_("The combination of your Fiskaly API key and secret is incorrect. " \
                                        "Please update them in your company settings"))
            self.sudo().l10n_de_fiskaly_dsfinvk_token = auth_response.json()['access_token']
        headers = {'Authorization': 'Bearer ' + self.sudo().l10n_de_fiskaly_dsfinvk_token}
        return url, headers

    def _l10n_de_fiskaly_dsfinvk_rpc(self, method, path, json=None, version=0, recursive=False):
        try:
            timeout = 300
            url, headers = self._l10n_de_fiskaly_dsfinvk_auth(version)
            if method == 'GET':
                res = requests.get(url + path, headers=headers, timeout=timeout)
            elif method == 'PUT':
                res = requests.put(url + path, headers=headers, json=json, timeout=timeout)
            else:
                raise UserError(_('Invalid method'))
            if res.status_code == 401 and not recursive:
                self.sudo().l10n_de_fiskaly_dsfinvk_token = None
                res = self._l10n_de_fiskaly_dsfinvk_rpc(method, path, json, version, True)
            return res
        except ConnectionError:
            raise UserError(_("Connection lost between Odoo and Fiskaly."))
        except ConnectTimeout:
            raise UserError(_("There are some connection issues between us and Fiskaly, try again later."))

    def _l10n_de_fiskaly_iap_rpc(self, path, params, version=1):
        endpoint = self.env['ir.config_parameter'].sudo().get_param('l10n_de_fiskaly_iap.endpoint', DEFAULT_ENDPOINT)
        base_url = '%s/%s' % (endpoint, version)
        response = jsonrpc(base_url + path, params=params)
        if 'error' in response:
            raise UserError(response['error'])
        return response

    def _l10n_de_check_required_fiskaly_fields(self):
        name = ' '.join(self.name.split())
        if name.isspace() or len(name) < 3:
            raise ValidationError(_("The name should be at least 3 characters long"))
        if not self.street or not self.street.strip():
            raise ValidationError(_("The street should not be empty"))
        if not self.zip or not self.zip.strip():
            raise ValidationError(_("The zip should not be empty"))
        if not self.city or not self.city.strip():
            raise ValidationError(_("The city should not be empty"))
        if not self.vat or not self.vat.strip():
            raise ValidationError(_("The VAT should not be empty"))

    def _l10n_de_create_db_payload(self):
        params = {
            'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            'company_id': self.id,
        }
        if self.l10n_de_fiskaly_organization_id:
            params['organization_id'] = self.l10n_de_fiskaly_organization_id
        return params

    def _l10n_de_create_organization_payload(self):
        self._l10n_de_check_required_fiskaly_fields()
        db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        data = {
            'name': '{0} [#{1}]'.format(self.name, db_uuid),  # To make sure the name is always unique
            'address_line1': self.street,
            'zip': self.zip,
            'town': self.city,
            'country_code': 'DEU',  # It will always be Germany since this module will never be active for others
            'display_name': self.name,
            'address_line2': self.street2,
            'vat_id': self.vat,
            'tax_number': self.l10n_de_stnr if self.l10n_de_stnr else '',
            'economy_id': self.l10n_de_widnr if self.l10n_de_widnr else '',
        }

        return {'data': data, **self._l10n_de_create_db_payload()}

    def l10n_de_action_fiskaly_register(self):
        """
        Send a request to Fiskaly in order to register the company at the financial authority.
        """
        self.ensure_one()
        if not self.l10n_de_fiskaly_organization_id:
            params = self._l10n_de_create_organization_payload()
            response = self._l10n_de_fiskaly_iap_rpc('/register', params)
            if not response.get('ignored'):
                if response.get('api_key'):
                    self.write({
                        'l10n_de_fiskaly_organization_id': response['organization_id'],
                        'l10n_de_fiskaly_api_key': response['api_key'],
                        'l10n_de_fiskaly_api_secret': response['api_secret'],
                    })
                else:   # the request to create credentials failed but the company was still well registered
                    self.l10n_de_fiskaly_organization_id = response['organization_id']

    def l10n_de_action_fiskaly_create_new_keys(self):
        self.ensure_one()

        params = self._l10n_de_create_db_payload()
        response = self._l10n_de_fiskaly_iap_rpc('/new_credentials', params=params)
        self.write({
            'l10n_de_fiskaly_api_key': response['api_key'],
            'l10n_de_fiskaly_api_secret': response['api_secret'],
        })
