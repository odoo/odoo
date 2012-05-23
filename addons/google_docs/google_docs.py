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

from osv import osv, fields
from tools.translate import _
try:
    import gdata.docs.data
    import gdata.docs.client
    from gdata.client import RequestError
    from gdata.docs.service import DOCUMENT_LABEL
    import gdata.auth
except ImportError:
    raise osv.except_osv(_('Google Docs Error!'), _('Please install gdata-python-client from http://code.google.com/p/gdata-python-client/downloads/list'))

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
        user_config = google_pool.default_get( cr, uid, {'user' : '' , 'password' : ''}, context=context)
        #login gmail account
        client = google_pool.google_login( user_config['user'], user_config['password'], type='docs_client', context=context)
        if not client:
            raise osv.except_osv( _('Google Docs Error!'), _("Check your google configuration in users/synchronization"))
        return client

    def create_empty_google_doc(self, cr, uid, res_model, res_id, context=None):
        '''Create a new google document, empty and with a default type (txt)
           :param res_model: the object for which the google doc is created
           :param res_id: the Id of the object for which the google doc is created
           :return: the ID of the google document object created
        '''
        #login with the base account google module
        client = self._auth(cr, uid, context=context)
        # create the document in google docs
        local_resource = gdata.docs.data.Resource(gdata.docs.data.DOCUMENT_LABEL)
        #create a new doc in Google Docs 
        gdocs_resource = client.post(entry=local_resource, uri='https://docs.google.com/feeds/default/private/full/')
        # create an ir.attachment into the db
        self.create(cr, uid, {
            'res_model': res_model,
            'res_id': res_id,
            'type': 'url',
            'name': _('Google Doc'),
            'url': gdocs_resource.get_alternate_link().href,
        }, context=context)
        return gdocs_resource.resource_id.text

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
            original_resource = client.get_resource_by_id(gdoc_template_id)
            #copy the document you choose in the configuration
            copy_resource = client.copy_resource(original_resource, 'copy_%s' % original_resource.title.text)
        except:
            raise osv.except_osv(_('Google Docs Error!'), _("Your resource id is not correct. You can find the id in the google docs URL"))
        # create an ir.attachment
        self.create(cr, uid, {
            'res_model': res_model,
            'res_id': res_id,
            'type': 'url',
            'name': name_gdocs,
            'url': copy_resource.get_alternate_link().href
        }, context=context)
        return copy_resource.resource_id.text

    def google_doc_get(self, cr, uid, res_model, ids, context=None):
        '''
        Function called by the js, when no google doc are yet associated with a record, with the aim to create one. It
        will first seek for a google.docs.config associated with the model `res_model` to find out what's the template
        of google doc to copy (this is usefull if you want to start with a non-empty document, a type or a name 
        different than the default values). If no config is associated with the `res_model`, then a blank text document
        with a default name is created.
          :param res_model: the object for which the google doc is created
          :param ids: the list of ids of the objects for which the google doc is created. This list is supposed to have
            a length of 1 element only (batch processing is not supported in the code, though nothing really prevent it)
          :return: the google document object created
        '''
        assert len(ids) == 1, 'Creating google docs may only be done by one at a time'
        res_id = ids[0]
        pool_ir_attachment = self.pool.get('ir.attachment')
        pool_gdoc_config = self.pool.get('google.docs.config')
        name_gdocs = ''
        model_fields_dic = self.pool.get(res_model).read(cr, uid, res_id, [], context=context)

        # check if a model is configured with a template
        google_docs_config = pool_gdoc_config.search(cr, uid, [('model_id', '=', res_model)], context=context)
        if google_docs_config:
            name_gdocs = pool_gdoc_config.browse(cr, uid, google_docs_config, context=context)[0].name_template
            name_gdocs = name_gdocs % model_fields_dic
            google_template_id = pool_gdoc_config.browse(cr, uid, google_docs_config[0], context=context).gdocs_resource_id
            google_document = pool_ir_attachment.copy_gdoc(cr, uid, res_model, res_id, name_gdocs, google_template_id, context=context)
        else:
            google_document = pool_ir_attachment.create_empty_google_doc(cr, uid, res_model, res_id, context=context)
        return google_document

class config(osv.osv):
    _name = 'google.docs.config'
    _description = "Google Docs templates config"

    _columns = {
        'model_id': fields.many2one('ir.model', 'Model'),
        'gdocs_resource_id': fields.char('Google resource ID', size=64,help='''
This is the id of the template document, on google side. You can find it thanks to its URL: 
*for a text document with url like `https://docs.google.com/a/openerp.com/document/d/123456789/edit`, the ID is `document:123456789`
*for a spreadsheet document with url like `https://docs.google.com/a/openerp.com/spreadsheet/ccc?key=123456789#gid=0`, the ID is `spreadsheet:123456789`
*for a presentation (slide show) document with url like `https://docs.google.com/a/openerp.com/presentation/d/123456789/edit#slide=id.p`, the ID is `presentation:123456789`
*for a drawing document with url like `https://docs.google.com/a/openerp.com/drawings/d/123456789/edit`, the ID is `drawings:123456789`
...
'''),
        'name_template': fields.char('GDoc name template ', size=64, help='This is the name which appears on google side'),
    }

    _defaults = {
        'name_template': 'gdoc_%(name)s',
    }
config()
