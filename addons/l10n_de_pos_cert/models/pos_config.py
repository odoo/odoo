# -*- coding: utf-8 -*-

from odoo import models, fields, _, api
from odoo.exceptions import ValidationError, UserError
import requests
from requests.exceptions import ConnectTimeout
import uuid


class PosConfig(models.Model):
    _inherit = 'pos.config'
    fiskaly_tss_id = fields.Char(string="TSS ID", readonly=True)
    fiskaly_client_id = fields.Char(string="Client ID", readonly=True)
    create_tss_flag = fields.Boolean(default=False)
    is_company_country_germany = fields.Boolean(compute='_compute_is_company_country_germany')

    @api.depends('company_id.country_id')
    def _compute_is_company_country_germany(self):
        for config in self:
            config.is_company_country_germany = config.company_id.country_id == self.env.ref('base.de')

    def _check_fiskaly_key_secret(self):
        if not self.company_id.fiskaly_key or not self.company_id.fiskaly_secret:
            raise UserError(_("You have to set your Fiskaly key and secret in your company settings."))

    def _check_fiskaly_tss_client_ids(self):
        if not self.fiskaly_tss_id or not self.fiskaly_client_id:
            raise UserError(_("You have to set your Fiskaly TSS ID and Client ID in your PoS settings."))

    def open_ui(self):
        if not self.company_id.country_id:
            raise UserError(_("You have to set a country in your company setting."))
        if self.company_id.country_id == self.env.ref('base.de'):
            self._check_fiskaly_key_secret()
            self._check_fiskaly_tss_client_ids()
        return super(PosConfig, self).open_ui()

    @api.model
    def create(self, values):
        res = super(PosConfig, self).create(values)
        if values.get('create_tss_flag') is True:
            res.create_tss_process()
        return res

    def write(self, values):
        res = super(PosConfig, self).write(values)
        if values.get('create_tss_flag') is True:
            self.create_tss_process()
        return res

    def unlink(self):
        if self.create_tss_flag:
            cache = {
                'fiskaly_tss_id': self.fiskaly_tss_id,
                'fiskaly_secret': self.company_id.fiskaly_secret,
                'fiskaly_key': self.company_id.fiskaly_key
            }
            res = super(PosConfig, self).unlink()
            self.delete_tss(cache)
            return res
        else:
            return super(PosConfig, self).unlink()

    def create_tss_process(self):
        if self.create_tss_flag and not self.fiskaly_tss_id and not self.fiskaly_client_id:
            try:
                headers = self.fiskaly_authentication(self.company_id.fiskaly_secret, self.company_id.fiskaly_key)
                phantom_tss = self.retrieve_phantom_tss(headers)
                if not phantom_tss:
                    tss_id = self.create_fiskaly_tss(headers)
                    client_id = self.create_fiskaly_client(headers, tss_id)
                    self.write({'fiskaly_tss_id': tss_id, 'fiskaly_client_id': client_id})
                else:
                    if 'fiskaly_client_id' not in phantom_tss:
                        phantom_tss['fiskaly_client_id'] = self.create_fiskaly_client(headers, phantom_tss['fiskaly_tss_id'])
                    self.write(phantom_tss)
            except ConnectionError:
                #  kind of useless? If the odoo server lose connection, the error won't appear to the client
                raise ValidationError(_("Connection error between Odoo and Fiskaly."))
            except ConnectTimeout:
                raise ValidationError(_("There are some connection issues between us and Fiskaly, try again later."))

    def delete_tss(self, cache):
        try:
            url = self.env['ir.config_parameter'].sudo().get_param('fiskaly_kassensichv_api_url')
            timeout = float(self.env['ir.config_parameter'].sudo().get_param('fiskaly_api_timeout'))

            headers = self.fiskaly_authentication(cache['fiskaly_secret'], cache['fiskaly_key'])
            disable_tss_response = requests.put('{0}tss/{1}'.format(url, cache['fiskaly_tss_id']),
                                                json={'state': 'DISABLED'}, headers=headers,
                                                timeout=timeout)
            if disable_tss_response.status_code != 200:
                raise ValidationError(_("It seems there are some issues, please try again later."))
        except ConnectionError:
            raise ValidationError(_("Connection error between Odoo and Fiskaly."))
        except ConnectTimeout:
            raise ValidationError(_("There are some connection issues between us and Fiskaly, try again later."))

    def fiskaly_authentication(self, secret, key):
        url = self.env['ir.config_parameter'].sudo().get_param('fiskaly_kassensichv_api_url')
        timeout = float(self.env['ir.config_parameter'].sudo().get_param('fiskaly_api_timeout'))

        auth_response = requests.post(url + 'auth', json={
            'api_secret': secret,
            'api_key': key
        }, timeout=timeout)
        if auth_response.status_code == 401:
            raise ValidationError(_("The combination of your Fiskaly API key and secret is incorrect. " +
                                    "Please update them in your company settings"))
        headers = {'Authorization': 'Bearer ' + auth_response.json()['access_token']}
        return headers

    def retrieve_phantom_tss(self, headers):
        url = self.env['ir.config_parameter'].sudo().get_param('fiskaly_kassensichv_api_url')
        timeout = float(self.env['ir.config_parameter'].sudo().get_param('fiskaly_api_timeout'))

        # We first check if we've already created a TSS and Client which are not linked yet to Odoo
        get_client_list_response = requests.get(url + 'client', headers=headers, timeout=timeout)
        client_list = get_client_list_response.json()['data']
        for client in client_list:
            if client['serial_number'] == self.uuid:
                return {'fiskaly_tss_id': client['tss_id'], 'fiskaly_client_id': client['_id']}
        # Otherwise we try to find a free TSS
        initialized_tss_list = []
        get_tss_list_response = requests.get(url + 'tss', headers=headers, timeout=timeout)
        for tss in get_tss_list_response.json()['data']:
            if tss['state'] == 'INITIALIZED':
                initialized_tss_list.append(tss['_id'])
        for tss_id in initialized_tss_list:
            found = False
            for i in range(len(client_list)):
                if client_list[i]['tss_id'] == tss_id:
                    del client_list[i]
                    found = True
                    break
            if not found:
                return {'fiskaly_tss_id': tss_id}

        return None

    def create_fiskaly_tss(self, headers):
        url = self.env['ir.config_parameter'].sudo().get_param('fiskaly_kassensichv_api_url')
        timeout = float(self.env['ir.config_parameter'].sudo().get_param('fiskaly_api_timeout'))

        tss_id = str(uuid.uuid4())
        tss_creation_response = requests.put('{0}tss/{1}'.format(url, tss_id),
                                             json={'state': 'INITIALIZED', 'description': ''}, headers=headers,
                                             timeout=timeout)
        if tss_creation_response.status_code != 200:
            raise ValidationError(_("It seems there are some issues, please try again later."))

        return tss_id

    def create_fiskaly_client(self, headers, tss_id):
        url = self.env['ir.config_parameter'].sudo().get_param('fiskaly_kassensichv_api_url')
        timeout = float(self.env['ir.config_parameter'].sudo().get_param('fiskaly_api_timeout'))

        client_id = str(uuid.uuid4())
        client_creation_response = requests.put('{0}tss/{1}/client/{2}'.format(url, tss_id, client_id),
                                                json={'serial_number': self.uuid}, headers=headers, timeout=timeout)
        if client_creation_response.status_code != 200:
            raise ValidationError(_("It seems there are some issues, please try again later."))

        return client_id