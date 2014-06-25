##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2012 OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import logging

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools.translate import _

import werkzeug.urls
import urllib2
import json
import re
import openerp

_logger = logging.getLogger(__name__)


class config(osv.Model):
    _name = 'google.drive.config'
    _description = "Google Drive templates config"

    def get_google_drive_url(self, cr, uid, config_id, res_id, template_id, context=None):
        config = self.browse(cr, SUPERUSER_ID, config_id, context=context)
        model = config.model_id
        filter_name = config.filter_id and config.filter_id.name or False
        record = self.pool.get(model.model).read(cr, uid, res_id, [], context=context)
        record.update({'model': model.name, 'filter': filter_name})
        name_gdocs = config.name_template
        try:
            name_gdocs = name_gdocs % record
        except:
            raise osv.except_osv(_('Key Error!'), _("At least one key cannot be found in your Google Drive name pattern"))

        attach_pool = self.pool.get("ir.attachment")
        attach_ids = attach_pool.search(cr, uid, [('res_model', '=', model.model), ('name', '=', name_gdocs), ('res_id', '=', res_id)])
        url = False
        if attach_ids:
            attachment = attach_pool.browse(cr, uid, attach_ids[0], context)
            url = attachment.url
        else:
            url = self.copy_doc(cr, uid, res_id, template_id, name_gdocs, model.model, context).get('url')
        return url

    def get_access_token(self, cr, uid, scope=None, context=None):
        ir_config = self.pool['ir.config_parameter']
        google_drive_refresh_token = ir_config.get_param(cr, SUPERUSER_ID, 'google_drive_refresh_token')
        user_is_admin = self.pool['res.users'].has_group(cr, uid, 'base.group_erp_manager')
        if not google_drive_refresh_token:
            if user_is_admin:
                model, action_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'base_setup', 'action_general_configuration')
                msg = _("You haven't configured 'Authorization Code' generated from google, Please generate and configure it .")
                raise openerp.exceptions.RedirectWarning(msg, action_id, _('Go to the configuration panel'))
            else:
                raise osv.except_osv(_('Error!'), _("Google Drive is not yet configured. Please contact your administrator."))
        google_drive_client_id = ir_config.get_param(cr, SUPERUSER_ID, 'google_drive_client_id')
        google_drive_client_secret = ir_config.get_param(cr, SUPERUSER_ID, 'google_drive_client_secret')
        #For Getting New Access Token With help of old Refresh Token

        data = werkzeug.url_encode(dict(client_id=google_drive_client_id,
                                     refresh_token=google_drive_refresh_token,
                                     client_secret=google_drive_client_secret,
                                     grant_type="refresh_token",
                                     scope=scope or 'https://www.googleapis.com/auth/drive'))
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept-Encoding": "gzip, deflate"}
        try:
            req = urllib2.Request('https://accounts.google.com/o/oauth2/token', data, headers)
            content = urllib2.urlopen(req).read()
        except urllib2.HTTPError:
            if user_is_admin:
                model, action_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'base_setup', 'action_general_configuration')
                msg = _("Something went wrong during the token generation. Please request again an authorization code .")
                raise openerp.exceptions.RedirectWarning(msg, action_id, _('Go to the configuration panel'))
            else:
                raise osv.except_osv(_('Error!'), _("Google Drive is not yet configured. Please contact your administrator."))
        content = json.loads(content)
        return content.get('access_token')

    def copy_doc(self, cr, uid, res_id, template_id, name_gdocs, res_model, context=None):
        ir_config = self.pool['ir.config_parameter']
        google_web_base_url = ir_config.get_param(cr, SUPERUSER_ID, 'web.base.url')
        access_token = self.get_access_token(cr, uid, context=context)
        # Copy template in to drive with help of new access token
        request_url = "https://www.googleapis.com/drive/v2/files/%s?fields=parents/id&access_token=%s" % (template_id, access_token)
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept-Encoding": "gzip, deflate"}
        try:
            req = urllib2.Request(request_url, None, headers)
            parents = urllib2.urlopen(req).read()
        except urllib2.HTTPError:
            raise osv.except_osv(_('Warning!'), _("The Google Template cannot be found. Maybe it has been deleted."))
        parents_dict = json.loads(parents)

        record_url = "Click on link to open Record in OpenERP\n %s/?db=%s#id=%s&model=%s" % (google_web_base_url, cr.dbname, res_id, res_model)
        data = {"title": name_gdocs, "description": record_url, "parents": parents_dict['parents']}
        request_url = "https://www.googleapis.com/drive/v2/files/%s/copy?access_token=%s" % (template_id, access_token)
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        data_json = json.dumps(data)
        # resp, content = Http().request(request_url, "POST", data_json, headers)
        req = urllib2.Request(request_url, data_json, headers)
        content = urllib2.urlopen(req).read()
        content = json.loads(content)
        res = {}
        if content.get('alternateLink'):
            attach_pool = self.pool.get("ir.attachment")
            attach_vals = {'res_model': res_model, 'name': name_gdocs, 'res_id': res_id, 'type': 'url', 'url': content['alternateLink']}
            res['id'] = attach_pool.create(cr, uid, attach_vals)
            # Commit in order to attach the document to the current object instance, even if the permissions has not been written.
            cr.commit()
            res['url'] = content['alternateLink']
            key = self._get_key_from_url(res['url'])
            request_url = "https://www.googleapis.com/drive/v2/files/%s/permissions?emailMessage=This+is+a+drive+file+created+by+OpenERP&sendNotificationEmails=false&access_token=%s" % (key, access_token)
            data = {'role': 'writer', 'type': 'anyone', 'value': '', 'withLink': True}
            try:
                req = urllib2.Request(request_url, json.dumps(data), headers)
                urllib2.urlopen(req)
            except urllib2.HTTPError:
                raise self.pool.get('res.config.settings').get_config_warning(cr, _("The permission 'reader' for 'anyone with the link' has not been written on the document"), context=context)
            user = self.pool['res.users'].browse(cr, uid, uid, context=context)
            if user.email:
                data = {'role': 'writer', 'type': 'user', 'value': user.email}
                try:
                    req = urllib2.Request(request_url, json.dumps(data), headers)
                    urllib2.urlopen(req)
                except urllib2.HTTPError:
                    pass
        return res 

    def get_google_drive_config(self, cr, uid, res_model, res_id, context=None):
        '''
        Function called by the js, when no google doc are yet associated with a record, with the aim to create one. It
        will first seek for a google.docs.config associated with the model `res_model` to find out what's the template
        of google doc to copy (this is usefull if you want to start with a non-empty document, a type or a name
        different than the default values). If no config is associated with the `res_model`, then a blank text document
        with a default name is created.
          :param res_model: the object for which the google doc is created
          :param ids: the list of ids of the objects for which the google doc is created. This list is supposed to have
            a length of 1 element only (batch processing is not supported in the code, though nothing really prevent it)
          :return: the config id and config name
        '''
        if not res_id:
            raise osv.except_osv(_('Google Drive Error!'), _("Creating google drive may only be done by one at a time."))
        # check if a model is configured with a template
        config_ids = self.search(cr, uid, [('model_id', '=', res_model)], context=context)
        configs = []
        for config in self.browse(cr, uid, config_ids, context=context):
            if config.filter_id:
                if (config.filter_id.user_id and config.filter_id.user_id.id != uid):
                    #Private
                    continue
                domain = [('id', 'in', [res_id])] + eval(config.filter_id.domain)
                local_context = context and context.copy() or {}
                local_context.update(eval(config.filter_id.context))
                google_doc_configs = self.pool.get(config.filter_id.model_id).search(cr, uid, domain, context=local_context)
                if google_doc_configs:
                    configs.append({'id': config.id, 'name': config.name})
            else:
                configs.append({'id': config.id, 'name': config.name})
        return configs

    def _get_key_from_url(self, url):
        mo = re.search("(key=|/d/)([A-Za-z0-9-_]+)", url)
        if mo:
            return mo.group(2)
        return None

    def _resource_get(self, cr, uid, ids, name, arg, context=None):
        result = {}
        for data in self.browse(cr, uid, ids, context):
            mo = self._get_key_from_url(data.google_drive_template_url)
            if mo:
                result[data.id] = mo
            else:
                raise osv.except_osv(_('Incorrect URL!'), _("Please enter a valid Google Document URL."))
        return result

    def _client_id_get(self, cr, uid, ids, name, arg, context=None):
        result = {}
        client_id = self.pool['ir.config_parameter'].get_param(cr, SUPERUSER_ID, 'google_drive_client_id')
        for config_id in ids:
            result[config_id] = client_id
        return result

    _columns = {
        'name': fields.char('Template Name', required=True),
        'model_id': fields.many2one('ir.model', 'Model', ondelete='set null', required=True),
        'model': fields.related('model_id', 'model', type='char', string='Model', readonly=True),
        'filter_id': fields.many2one('ir.filters', 'Filter', domain="[('model_id', '=', model)]"),
        'google_drive_template_url': fields.char('Template URL', required=True, size=1024),
        'google_drive_resource_id': fields.function(_resource_get, type="char", string='Resource Id'),
        'google_drive_client_id': fields.function(_client_id_get, type="char", string='Google Client '),
        'name_template': fields.char('Google Drive Name Pattern', help='Choose how the new google drive will be named, on google side. Eg. gdoc_%(field_name)s', required=True),
        'active': fields.boolean('Active'),
    }

    def onchange_model_id(self, cr, uid, ids, model_id, context=None):
        res = {}
        if model_id:
            model = self.pool['ir.model'].browse(cr, uid, model_id, context=context)
            res['value'] = {'model': model.model}
        else:
            res['value'] = {'filter_id': False, 'model': False}
        return res

    _defaults = {
        'name_template': 'Document %(name)s',
        'active': True,
    }

    def _check_model_id(self, cr, uid, ids, context=None):
        config_id = self.browse(cr, uid, ids[0], context=context)
        if config_id.filter_id and config_id.model_id.model != config_id.filter_id.model_id:
            return False
        return True

    _constraints = [
        (_check_model_id, 'Model of selected filter is not matching with model of current template.', ['model_id', 'filter_id']),
    ]

    def get_google_scope(self):
        return 'https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/drive.file'


class base_config_settings(osv.TransientModel):
    _inherit = "base.config.settings"

    _columns = {
        'google_drive_authorization_code': fields.char('Authorization Code'),
        'google_drive_uri': fields.char('URI', readonly=True, help="The URL to generate the authorization code from Google"),
    }
    _defaults = {
        'google_drive_uri': lambda s, cr, uid, c: s.pool['google.service']._get_google_token_uri(cr, uid, 'drive', scope=s.pool['google.drive.config'].get_google_scope(), context=c),
        'google_drive_authorization_code': lambda s, cr, uid, c: s.pool['ir.config_parameter'].get_param(cr, SUPERUSER_ID, 'google_drive_authorization_code', context=c),
    }

    def set_google_authorization_code(self, cr, uid, ids, context=None):
        ir_config_param = self.pool['ir.config_parameter']
        config = self.browse(cr, uid, ids[0], context)
        auth_code = config.google_drive_authorization_code
        if auth_code and auth_code != ir_config_param.get_param(cr, uid, 'google_drive_authorization_code', context=context):
            refresh_token = self.pool['google.service'].generate_refresh_token(cr, uid, 'drive', config.google_drive_authorization_code, context=context)
            ir_config_param.set_param(cr, uid, 'google_drive_authorization_code', auth_code, groups=['base.group_system'])
            ir_config_param.set_param(cr, uid, 'google_drive_refresh_token', refresh_token, groups=['base.group_system'])
