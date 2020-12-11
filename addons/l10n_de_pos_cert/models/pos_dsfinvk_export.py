# -*- coding: utf-8 -*-
import base64

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import uuid
import requests
from datetime import datetime
from requests.exceptions import ConnectTimeout


class PosDsfinvkExport(models.Model):
    _name = 'pos.dsfinvk_export'

    name = fields.Char(required=True)
    fiskaly_export_uuid = fields.Char(string="Export uuid", readonly=True, copy=False)
    start_datetime = fields.Datetime(required=True)
    end_datetime = fields.Datetime(required=True)
    state = fields.Selection([('pending', "Pending"), ('working', "Working"), ('completed', "Completed"),
                              ('cancelled', "Cancelled"), ('expired', "Expired"), ('deleted', "Deleted")],
                             readonly=True)
    expiration_datetime = fields.Datetime(readonly=True)
    config_id = fields.Many2one('pos.config', string="Point of sale")
    error_message = fields.Char(readonly=True)

    @api.model
    def create(self, values):
        res = super(PosDsfinvkExport, self).create(values)
        res.write({'fiskaly_export_uuid': uuid.uuid4()})
        res.trigger_fiskaly_export()
        return res

    @api.constrains('start_datetime', 'end_datetime')
    def _check_datetime(self):
        for export in self:
            if export.start_datetime > export.end_datetime:
                raise ValidationError(_('The start datetime should be smaller than the end datetime'))

    @api.constrains('config_id.fiskaly_client_id', 'config_id.fiskaly_tss_id')
    def _check_fiskaly_client_tss(self):
        for export in self:
            if export.config_id and (not export.config_id.fiskaly_client_id or not export.config_id.fiskaly_tss_id):
                raise ValidationError(_('You can only export the data of a point of sale linked to a TSS.'))

    def _fiskaly_authentication(self, url, timeout):
        try:
            auth_response = requests.post(url + 'auth', json={
                'api_secret': self.env.company.fiskaly_secret,
                'api_key': self.env.company.fiskaly_key
            }, timeout=timeout)
            headers = {'Authorization': 'Bearer ' + auth_response.json()['access_token']}
        except ConnectionError:
            #  kind of useless? If the odoo server lose connection, the error won't appear to the client
            raise UserError(_("Connection lost between Odoo and Fiskaly."))
        except ConnectTimeout:
            raise UserError(_("There are some connection issues between us and Fiskaly, try again later."))

        return headers

    def trigger_fiskaly_export(self):
        url = self.env['ir.config_parameter'].sudo().get_param('fiskaly_dsfinvk_api_url')
        timeout = float(self.env['ir.config_parameter'].sudo().get_param('fiskaly_api_timeout'))
        headers = self._fiskaly_authentication(url, timeout)
        payload = {
            'start_date': self.start_datetime.timestamp(),
            'end_date': self.end_datetime.timestamp(),
        }
        if self.config_id:
            payload['client_id'] = self.config_id.fiskaly_client_id
        trigger_resp = requests.put('{0}exports/{1}'.format(url, self.fiskaly_export_uuid),
                                    json=payload, headers=headers, timeout=timeout)
        if trigger_resp.status_code == 404:
            raise ValidationError(_('There is no cash point closing with these data.'))
        elif trigger_resp.status_code != 200:
            raise UserError(_('An unknown error has occurred during the creation of the export.'))

        trigger_data = trigger_resp.json()
        values = {
            'state': trigger_data['state'].lower(),
            'expiration_datetime': datetime.fromtimestamp(trigger_data['time_expiration'])
        }
        if values['state'] == 'error':
            values['error_message'] = trigger_data['error']['message']
        self.write(values)

    def _retrieve_export_data(self, url, headers, timeout):
        retrieve_export_resp = requests.get('{0}exports/{1}'.format(url, self.fiskaly_export_uuid),
                                            headers=headers, timeout=timeout)
        if retrieve_export_resp.status_code == 404:
            raise ValidationError(_('The export does not exist at Fiskaly side'))
        elif retrieve_export_resp.status_code != 200:
            raise UserError(_('An unknown error has occurred, try again later or contact the support.'))

        return retrieve_export_resp.json()

    def action_refresh_state(self):
        url = self.env['ir.config_parameter'].sudo().get_param('fiskaly_dsfinvk_api_url')
        timeout = float(self.env['ir.config_parameter'].sudo().get_param('fiskaly_api_timeout'))
        headers = self._fiskaly_authentication(url, timeout)
        export_data = self._retrieve_export_data(url, headers, timeout)
        self.write({'state': export_data['state'].lower()})

    def action_download_export(self):
        url = self.env['ir.config_parameter'].sudo().get_param('fiskaly_dsfinvk_api_url')
        timeout = float(self.env['ir.config_parameter'].sudo().get_param('fiskaly_api_timeout'))
        headers = self._fiskaly_authentication(url, timeout)

        # We first check if the export has expired or not
        export_data = self._retrieve_export_data(url, headers, timeout)

        if export_data['state'] == 'COMPLETED':
            download_resp = requests.get('{0}exports/{1}/download'.format(url, self.fiskaly_export_uuid),
                                         headers=headers, timeout=timeout)
            file = self.env['pos.download_dsfinvk_export_wizard'].create({
                'file_name': self.name + '.tar',
                'file': base64.b64encode(download_resp.content)
            })

            return {
                'name': _('Download export'),
                'res_id': file.id,
                'res_model': 'pos.download_dsfinvk_export_wizard',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'view_id': self.env.ref('l10n_de_pos_cert.download_export_wizard_view').id,
                'view_mode': 'form',
                'view_type': 'form'
            }
        else:
            values = {'state': export_data['state'].lower()}
            if values['state'] == 'error':
                values['error_message'] = export_data['error']['message']
            self.write(values)
