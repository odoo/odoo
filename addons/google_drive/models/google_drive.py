# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import re
import urllib2
import werkzeug

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError
from odoo.tools.safe_eval import safe_eval as eval

from odoo.addons.google_account import TIMEOUT


class GoogleDriveConfig(models.Model):
    _name = 'google.drive.config'
    _description = "Google Drive templates config"

    name = fields.Char(string='Template Name', required=True)
    model_id = fields.Many2one('ir.model', string='Model', required=True)
    model = fields.Char(related='model_id.model', readonly=True)
    filter_id = fields.Many2one('ir.filters', string='Filter', domain="[('model_id', '=', model)]")
    google_drive_template_url = fields.Char(string='Template URL', required=True)
    google_drive_resource_id = fields.Char(compute='_compute_resource_id', string='Resource ID')
    google_drive_client_id = fields.Char(compute='_compute_client_id', string='Google Client')
    name_template = fields.Char(string='Google Drive Name Pattern', required=True, default="Document %(name)s",
                                help='Choose how the new google drive will be named, on google side. Eg. gdoc_%(field_name)s')
    active = fields.Boolean(default=True)

    def _compute_resource_id(self):
        for config in self:
            key = config._get_key_from_url(config.google_drive_template_url)
            if key:
                config.google_drive_resource_id = key
            else:
                raise UserError(_("Please enter a valid Google Document URL."))

    def _compute_client_id(self):
        client_id = self.env['ir.config_parameter'].sudo().get_param('google_drive_client_id')
        for config in self:
            config.google_drive_client_id = client_id

    @api.constrains('model_id', 'filter_id')
    def _check_model_id(self):
        if self.filter_id and self.filter_id.model_id != self.model_id.model:
            raise UserError(_('Model of selected filter is not matching with model of current template.'))
        return True

    @api.onchange('model_id')
    def onchange_model_id(self):
        if not self.model_id:
            self.filter_id = False

    @api.multi
    def get_google_drive_url(self, res_id, template_id):
        self.ensure_one()
        model = self.model_id
        record = self.env[self.model].browse(res_id).read()[0]
        record.update({'model': model.name, 'filter': self.filter_id.name})
        name_gdocs = self.name_template
        try:
            name_gdocs = name_gdocs % record
        except:
            raise UserError(_("At least one key cannot be found in your Google Drive name pattern"))

        attachment = self.env['ir.attachment'].search([
                       ('res_model', '=', model.model),
                       ('name', '=', name_gdocs),
                       ('res_id', '=', res_id)
                    ], limit=1)
        if attachment:
            return attachment.url
        else:
            return self.copy_doc(res_id, template_id, name_gdocs, model.model).get('url')

    @api.model
    def get_access_token(self, scope=None):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        google_drive_refresh_token = ICPSudo.get_param('google_drive_refresh_token')
        if not google_drive_refresh_token:
            if self.env.user._is_admin():
                raise RedirectWarning(_("You haven't configured 'Authorization Code' generated from google, Please generate and configure it ."),
                                      self.env.ref('base_setup.action_general_configuration').id,
                                      _('Go to the configuration panel'))
            else:
                raise UserError(_("Google Drive is not yet configured. Please contact your administrator."))
        google_drive_client_id = ICPSudo.get_param('google_drive_client_id')
        google_drive_client_secret = ICPSudo.get_param('google_drive_client_secret')
        #For Getting New Access Token With help of old Refresh Token

        data = werkzeug.url_encode(dict(client_id=google_drive_client_id,
                                    refresh_token=google_drive_refresh_token,
                                    client_secret=google_drive_client_secret,
                                    grant_type="refresh_token",
                                    scope=scope or 'https://www.googleapis.com/auth/drive'))
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        try:
            req = urllib2.Request('https://accounts.google.com/o/oauth2/token', data, headers)
            content = urllib2.urlopen(req, timeout=TIMEOUT).read()
        except urllib2.HTTPError:
            if self.env.user._is_admin():
                raise RedirectWarning(_("Something went wrong during the token generation. Please request again an authorization code ."),
                                      self.env.ref('base_setup.action_general_configuration').id,
                                      _('Go to the configuration panel'))
            else:
                raise UserError(_("Google Drive is not yet configured. Please contact your administrator."))
        return json.loads(content).get('access_token')

    @api.model
    def copy_doc(self, res_id, template_id, name_gdocs, res_model):
        google_web_base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        access_token = self.get_access_token()
        # Copy template in to drive with help of new access token
        request_url = "https://www.googleapis.com/drive/v2/files/%s?fields=parents/id&access_token=%s" % (template_id, access_token)
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        try:
            req = urllib2.Request(request_url, None, headers)
            parents = urllib2.urlopen(req, timeout=TIMEOUT).read()
        except urllib2.HTTPError:
            raise UserError(_("The Google Template cannot be found. Maybe it has been deleted."))
        parents_dict = json.loads(parents)

        record_url = "Click on link to open Record in Odoo\n %s/?db=%s#id=%s&model=%s" % (google_web_base_url, self.env.cr.dbname, res_id, res_model)
        request_url = "https://www.googleapis.com/drive/v2/files/%s/copy?access_token=%s" % (template_id, access_token)
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        data_json = json.dumps({"title": name_gdocs, "description": record_url, "parents": parents_dict['parents']})
        req = urllib2.Request(request_url, data_json, headers)
        content = json.loads(urllib2.urlopen(req, timeout=TIMEOUT).read())
        res = {}
        if content.get('alternateLink'):
            attach_vals = {'res_model': res_model, 'name': name_gdocs, 'res_id': res_id, 'type': 'url', 'url': content['alternateLink']}
            res['id'] = self.env['ir.attachment'].create(attach_vals).id
            # Commit in order to attach the document to the current object instance, even if the permissions has not been written.
            self.env.cr.commit()
            res['url'] = content['alternateLink']
            key = self._get_key_from_url(res['url'])
            request_url = "https://www.googleapis.com/drive/v2/files/%s/permissions?emailMessage=This+is+a+drive+file+created+by+Odoo&sendNotificationEmails=false&access_token=%s" % (key, access_token)
            try:
                req = urllib2.Request(request_url, json.dumps({'role': 'writer', 'type': 'anyone', 'value': '', 'withLink': True}), headers)
                urllib2.urlopen(req, timeout=TIMEOUT)
            except urllib2.HTTPError:
                raise self.env['res.config.settings'].get_config_warning(_("The permission 'reader' for 'anyone with the link' has not been written on the document"))
            if self.env.user.email:
                try:
                    req = urllib2.Request(request_url, json.dumps({'role': 'writer', 'type': 'user', 'value': self.env.user.email}), headers)
                    urllib2.urlopen(req, timeout=TIMEOUT)
                except urllib2.HTTPError:
                    pass
        return res

    @api.model
    def get_google_drive_config(self, res_model, res_id):
        '''
        Function called by the js, when no google doc are yet associated with a record, with the aim to create one. It
        will first seek for a google.docs.config associated with the model `res_model` to find out what's the template
        of google doc to copy (this is usefull if you want to start with a non-empty document, a type or a name
        different than the default values). If no config is associated with the `res_model`, then a blank text document
        with a default name is created.
          :param res_model: the object for which the google doc is created
          :return: the config id and config name
        '''
        if not res_id:
            raise UserError(_("Creating google drive may only be done by one at a time."))
        configs = []
        for config in self.search([('model_id', '=', res_model)]):
            if config.filter_id:
                if config.filter_id.user_id != self.env.user:
                    #Private
                    continue
                domain = [('id', 'in', [res_id])] + eval(config.filter_id.domain)
                local_context = dict(self.env.context)
                local_context.update(eval(config.filter_id.context))
                if self.env[config.filter_id.model_id].with_context(local_context).search(domain):
                    configs.append({'id': config.id, 'name': config.name})
            else:
                configs.append({'id': config.id, 'name': config.name})
        return configs

    def _get_key_from_url(self, url):
        match = re.search("(key=|/d/)([A-Za-z0-9-_]+)", url)
        if match:
            return match.group(2)
        return None

    def get_google_scope(self):
        return 'https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/drive.file'
