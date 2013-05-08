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
from datetime import datetime

from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools.translate import _
from urlparse import urlparse

_logger = logging.getLogger(__name__)

try:
    import gdata.docs.data
    import gdata.docs.client

    # API breakage madness in the gdata API - those guys are insane. 
    try:
        # gdata 2.0.15+
        gdata.docs.client.DocsClient.copy_resource
    except AttributeError:
        # gdata 2.0.14- : copy_resource() was copy()
        gdata.docs.client.DocsClient.copy_resource = gdata.docs.client.DocsClient.copy

    try:
        # gdata 2.0.16+
        gdata.docs.client.DocsClient.get_resource_by_id
    except AttributeError:
        try:
            # gdata 2.0.15+
            gdata.docs.client.DocsClient.get_resource_by_self_link
            def get_resource_by_id_2_0_16(self, resource_id, **kwargs):
                return self.GetResourceBySelfLink(
                    gdata.docs.client.RESOURCE_FEED_URI + ('/%s' % resource_id), **kwargs)
            gdata.docs.client.DocsClient.get_resource_by_id = get_resource_by_id_2_0_16
        except AttributeError:
            # gdata 2.0.14- : alias get_resource_by_id()
            gdata.docs.client.DocsClient.get_resource_by_id = gdata.docs.client.DocsClient.get_doc

    try:
        import atom.http_interface
        _logger.info('GData lib version `%s` detected' % atom.http_interface.USER_AGENT)
    except (ImportError, AttributeError):
        _logger.debug('GData lib version could not be detected', exc_info=True)

except ImportError:
    _logger.warning("Please install latest gdata-python-client from http://code.google.com/p/gdata-python-client/downloads/list")


class google_docs_ir_attachment(osv.osv):
    _inherit = 'ir.attachment'

    def _auth(self, cr, uid, context=None):
        '''
        Connexion with google base account
        @return client object for connexion
        '''
        #pool the google.login in google_base_account
        google_pool = self.pool.get('google.login')
        #get gmail password and login. We use default_get() instead of a create() followed by a read() on the 
        # google.login object, because it is easier. The keys 'user' and 'password' ahve to be passed in the dict
        # but the values will be replaced by the user gmail password and login.
        user_config = google_pool.default_get(cr, uid, {'user' : '' , 'password' : ''}, context=context)
        #login gmail account
        client = google_pool.google_login(user_config['user'], user_config['password'], type='docs_client', context=context)
        if not client:
            raise osv.except_osv(_('Google Drive Error!'), _("Check your google account configuration in Users/Users/Google Account."))
        _logger.info('Logged into google docs as %s', user_config['user'])
        return client

    def copy_gdoc(self, cr, uid, res_model, res_id, name_gdocs, gdoc_template_id, context=None):
        '''
        copy an existing document in google docs
           :param res_model: the object for which the google doc is created
           :param res_id: the Id of the object for which the google doc is created
           :param name_gdocs: the name of the future ir.attachment that will be created. Based on the google doc template foun.
           :param gdoc_template_id: the id of the google doc document to copy
           :return: the ID of the google document object created
        '''
        #login with the base account google module
        client = self._auth(cr, uid)
        # fetch and copy the original document
        try:
            doc = client.get_resource_by_id(gdoc_template_id)
            #copy the document you choose in the configuration
            copy_resource = client.copy_resource(doc, name_gdocs)
        except:
            raise osv.except_osv(_('Google Drive Error!'), _("Your resource id is not correct. You can find the id in the google docs URL."))
        # create an ir.attachment
        self.create(cr, uid, {
            'res_model': res_model,
            'res_id': res_id,
            'type': 'url',
            'name': name_gdocs,
            'url': copy_resource.get_alternate_link().href
        }, context=context)
        return copy_resource.resource_id.text

    def get_google_docs_config(self, cr, uid, res_model, res_id, context=None):
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
        pool_gdoc_config = self.pool.get('google.docs.config')
        # check if a model is configured with a template
        config_ids = pool_gdoc_config.search(cr, uid, [('model_id', '=', res_model)], context=context)
        configs = []
        for config  in pool_gdoc_config.browse(cr, SUPERUSER_ID, config_ids, context=context):
            if config.filter_id:
                if (config.filter_id.user_id and config.filter_id.user_id.id != uid):
                    #Private
                    continue
                google_doc_configs = self._filter(cr, uid, config, config.filter_id, res_id, context=context)
                if google_doc_configs: 
                    configs.append({'id': config.id, 'name': config.name})
            else:
                configs.append({'id': config.id, 'name': config.name})
        return configs
    
    def _filter(self, cr, uid, action, action_filter, record_ids, context=None):
        """ filter the list record_ids that satisfy the action filter """
        records = {}
        if record_ids and action_filter:
            if not action.model_id == action_filter.model_id:
                raise osv.except_osv(_('Warning!'), _("Something went wrong with the configuration of attachments with google drive.Please contact your Administrator to fix the problem."))
            model = self.pool.get(action_filter.model_id)
            domain = [('id', 'in', [record_ids])] + eval(action_filter.domain)
            ctx = dict(context or {})
            ctx.update(eval(action_filter.context))
            record_ids = model.search(cr, uid, domain, context=ctx)
        return record_ids
    
    def get_google_attachment(self, cr, uid, config_id, res_id, context=None):
        pool_gdoc_config = self.pool.get('google.docs.config')
        pool_model = self.pool.get("ir.model")
        attachment = {'url': False}
        config = pool_gdoc_config.browse(cr, SUPERUSER_ID, config_id, context=context)
        if config:
            res_model = config.model_id
            model_ids = pool_model.search(cr, uid, [('model','=',res_model)])
            if not model_ids:
                return attachment
            model = pool_model.browse(cr, uid, model_ids[0], context=context).name
            filter_name = config.filter_id and config.filter_id.name or False
            record = self.pool.get(res_model).read(cr, uid, res_id, [], context=context)
            record.update({'model': model,'filter':filter_name})
            name_gdocs = config.name_template or "%(name)s_%(model)s_%(filter)s_gdrive"
            try:
                name_gdocs = name_gdocs % record
            except:
                raise osv.except_osv(_('Key Error!'), _("Your Google Doc Name Pattern's key does not found in object."))
    
            attach_ids = self.search(cr, uid, [('res_model','=',res_model),('name','=',name_gdocs),('res_id','=',res_id)])
            if not attach_ids: 
                google_template_id = config.gdocs_resource_id
                attach_id = self.copy_gdoc(cr, uid, config.model_id, res_id, name_gdocs, google_template_id, context=context)
            else:
                attach_id = attach_ids[0] 
            attachments = self.browse(cr, uid, attach_id, context)
            attachment['url'] = attachments.url
        return attachment

class config(osv.osv):
    _name = 'google.docs.config'
    _description = "Google Drive templates config"
    
    def _list_all_models(self, cr, uid, context=None):
        cr.execute("SELECT model, name from ir_model order by name")
        return cr.fetchall()
    
    def _resource_get(self, cr, uid, ids, name, arg, context=None):
        result = {}
        for data in self.browse(cr, uid, ids, context):
            template_url = data.gdocs_template_url
            try:
                url = urlparse(template_url)
                res = url.path.split('/')
                resource = res[1]
                if res[1]== "spreadsheet":
                    key = url.query.split('=')[1]
                else:
                    key = res[3]
                res_id = resource + ":" + key
                result[data.id] = str(res_id)
            except:
                raise osv.except_osv(_('Incorrect URL!'), _("Please enter a valid URL."))
        return result

    _columns = {
        'name' : fields.char('Template Name', required=True, size=1024),
        'model_id': fields.selection(_list_all_models, 'Model', required=True),
        'filter_id' : fields.many2one('ir.filters', 'Filter'),
        'gdocs_template_url': fields.char('Template URL', required=True, size=1024),
        'gdocs_resource_id' : fields.function(_resource_get,type="char" ,string='Resource Id',store=True),
        'name_template': fields.char('Google Drive Name Pattern', size=64, help='Choose how the new google drive will be named, on google side. Eg. gdoc_%(field_name)s', required=True),
            }

    def onchange_model_id(self, cr, uid, ids, model_id, context=None):
         res = {'domain':{'filter_id':[]}}
         if model_id:
            res['domain'] = {'filter_id': [('model_id', '=', model_id)]}
         else:
             res['value'] = {'filter_id': False}
         return res

    _defaults = {
        'name_template': '%(name)s_%(model)s_%(filter)s_gdrive',
    }
    def _check_model_id(self, cr, uid, ids, context=None):
        config_id = self.browse(cr, uid, ids[0], context=context)
        if config_id.filter_id.id and config_id.model_id != config_id.filter_id.model_id:
            return False
        return True

    _constraints = [
        (_check_model_id, 'Model of selected filter is not matching with model of current template.', ['model_id','filter_id']),
    ]

config()
