# -*- coding: utf-8 -*-
import base64

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import uuid


class PosDsfinvkExport(models.Model):
    _name = 'l10n_de_pos.dsfinvk_export'
    _description = 'This is the model that can download the data export from the DSFinV-K service in case of an audit.'

    config_id = fields.Many2one('pos.config', string="Point of Sale",
        help='Select a point of sale if you only want to export the data of the chosen point of sale. Leave it blank if you wish to export the data of all point of sale')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    l10n_de_fiskaly_export_uuid = fields.Char(string="Export Uuid", readonly=True, copy=False, default=lambda s: uuid.uuid4(), help='The uuid of the export at Fiskaly')
    start_datetime = fields.Datetime(string="Start Datetime", required=True, help='Only export data with dates larger than or equal to the given start date')
    end_datetime = fields.Datetime(string="End Datetime", required=True, help='Only export data with dates smaller than or equal to the given start date')
    state = fields.Selection([('pending', "Pending"), ('working', "Working"), ('completed', "Completed"), ('cancelled', "Cancelled"),
                              ('expired', "Expired"), ('deleted', "Deleted"), ('error', "Error")], readonly=True)

    @api.constrains('start_datetime', 'end_datetime')
    def _check_datetime(self):
        for export in self:
            if export.start_datetime > export.end_datetime:
                raise ValidationError(_('The start datetime should be smaller than the end datetime'))

    @api.constrains('config_id')
    def _check_fiskaly_client_tss(self):
        for export in self:
            if export.config_id and (not export.config_id.l10n_de_fiskaly_client_id or not export.config_id.l10n_de_fiskaly_tss_id):
                raise ValidationError(_('You can only export the data of a point of sale linked to a TSS.'))

    @api.model_create_multi
    def create(self, vals_list):
        exports = super().create(vals_list)
        for export in exports:
            export._l10n_de_trigger_fiskaly_export()
        return exports

    def _l10n_de_trigger_fiskaly_export(self):
        json = {
            'start_date': self.start_datetime.timestamp(),
            'end_date': self.end_datetime.timestamp(),
        }
        if self.config_id:
            json['client_id'] = self.config_id.l10n_de_fiskaly_client_id
        trigger_resp = self.company_id._l10n_de_fiskaly_dsfinvk_rpc('PUT', '/exports/%s' % self.l10n_de_fiskaly_export_uuid, json)

        if trigger_resp.status_code == 404:
            raise ValidationError(_('There is no cash point closing with these data.'))
        else:
            trigger_resp.raise_for_status()

        trigger_data = trigger_resp.json()
        values = {
            'state': trigger_data['state'].lower(),
        }
        self.write(values)

    def l10n_de_action_refresh_state(self):
        export_data = self.company_id._l10n_de_fiskaly_dsfinvk_rpc('GET', '/exports/%s' % self.l10n_de_fiskaly_export_uuid).json()
        values = {'state': export_data['state'].lower()}
        self.write(values)

    def l10n_de_action_download_export(self):
        """
        Download the export through Fiskaly. What is received from them is a .tar file
        https://developer.fiskaly.com/api/dsfinvk/v0/#operation/getExportDownload
        """
        # check locally in ir.attachment
        attachment = self.env['ir.attachment'].search([('res_model', '=', 'l10n_de_pos.dsfinvk_export'), ('res_id', '=', self.id)])
        if attachment:
            return {
                'target': 'new',
                'type': 'ir.actions.act_url',
                'url': '/web/content/%s?download=1' % attachment.id
            }

        # We first check if the export has expired or not
        export_data = self.company_id._l10n_de_fiskaly_dsfinvk_rpc('GET', '/exports/%s' % self.l10n_de_fiskaly_export_uuid).json()

        if export_data['state'] == 'COMPLETED':
            download_resp = self.company_id._l10n_de_fiskaly_dsfinvk_rpc('GET', '/exports/%s/download' % self.l10n_de_fiskaly_export_uuid)
            download_resp.raise_for_status()

            attachment = self.env['ir.attachment'].create({
                'name': "dsfinvk-%s-%s.tar" % (self.start_datetime.strftime("%Y-%m-%d %H:%M:%S"), self.end_datetime.strftime("%Y-%m-%d %H:%M:%S")),
                'datas': base64.b64encode(download_resp.content),
                'res_model': 'l10n_de_pos.dsfinvk_export',
                'res_id': self.id
            })
            return {
                'target': 'new',
                'type': 'ir.actions.act_url',
                'url': '/web/content/%s?download=1' % attachment.id
            }

        else:
            values = {'state': export_data['state'].lower()}
            self.write(values)
