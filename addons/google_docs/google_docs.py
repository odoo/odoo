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

    def _auth(self, cr, uid,context=None):
        '''
        Connexion with google base account
        @return client object for connexion
        '''
        #pool the google.login in google_base_account
        google_pool = self.pool.get('google.login')
        
        #get gmail password and login
        user_config = google_pool.default_get( cr, uid, {'user' : '' , 'password' : ''},context=context)
        #login gmail account
        client = google_pool.google_login( user_config['user'], user_config['password'], type='docs_client', context=context)
        if not client:
            raise osv.except_osv(('Google Docs Error!'),("Check your google configuration in users/synchronization") )
        return client

    def create_empty_google_doc(self, cr, uid, name_gdocs, model, ids, type_doc,context=None):
        '''Associate a copy of the gdoc identified by 'gdocs_res_id' to the current entity.
           @param cr: the current row from the database cursor.
           @param uid: the current user ID, for security checks.
           @param model: the current model name.
           @param type_doc: text, spreadsheet or slide.
           @return the document object.
           @return False if the google_base_account hasn't been configured yet.
        '''
        #login with the base account google module
        client = self._auth(cr, uid,context=context)
        # create the document in google docs
        local_resource = gdata.docs.data.Resource(gdata.docs.data.DOCUMENT_LABEL)
        #create a new doc in Google Docs 
        gdocs_resource = client.post(entry=local_resource, uri='https://docs.google.com/feeds/default/private/full/')
        # register into the db
        self.create(cr, uid, {
            'res_model': model,
            'res_id': ids[0],
            'type': 'url',
            'name': 'Google Doc',
            'url': gdocs_resource.get_alternate_link().href,
        },context=context)
        
        
        return 1

    def copy_gdoc(self, cr, uid, name_gdocs, model, google_res_id, ids,context=None):
        '''
        copy an existing document in google docs
        '''
        client = self._auth(cr, uid)
        # fetch and copy the original document
        try:
            original_resource = client.get_resource_by_id(google_res_id)
            #copy the document you choose in the configuration
            copy_resource = client.copy_resource(original_resource,'copy_%s' % original_resource.title.text)
        except:
            raise osv.except_osv(('Google Docs Error!'),("Your ressource id is not correct. You can find the id in the google docs URL") )
        # register into the db
        self.create(cr, uid, {
            'res_model': model,
            'res_id': ids[0],
            'type': 'url',
            'name': name_gdocs,
            'url': copy_resource.get_alternate_link().href
        },context=context)

        return copy_resource

class google_docs(osv.osv):
    _name = 'google.docs'

    def doc_get(self, cr, uid, model, id, type_doc,context=None):
        ir_attachment_ref = self.pool.get('ir.attachment')
        pool_gdoc_config = self.pool.get('google.docs.config')
        google_docs_config = pool_gdoc_config.search(cr, uid, [('model_id', '=', model)])
        name_gdocs=''
        model_fields_dic = self.pool.get(model).read(cr,uid,id,[])
        
        if google_docs_config:
            name_gdocs = pool_gdoc_config.browse(cr,uid,google_docs_config,context=context)[0].name_template
            name_gdocs = name_gdocs % model_fields_dic[0]
        
        # check if a model is configurate with a template
        if google_docs_config:
            for google_config in self.pool.get('google.docs.config').browse(cr,uid,google_docs_config,context=context):
                google_res_id = google_config.gdocs_resource_id
            google_document = ir_attachment_ref.copy_gdoc(cr, uid,name_gdocs ,model,google_res_id, id)
        else:
            google_document = ir_attachment_ref.create_empty_google_doc(cr, uid,name_gdocs, model, id, type_doc)
            return -1


class config(osv.osv):
    _name = 'google.docs.config'
    _description = "Google Docs templates config"

    _columns = {
        'model_id': fields.many2one('ir.model', 'Model'),
        'gdocs_resource_id': fields.char('Google resource ID', size=64,help='This is the id of the template document you kind find it in the URL'),
        'name_template': fields.char('GDoc name template ', size=64, help='This is the name which appears on google side'),
    }

    _defaults = {
        'name_template': 'pr_%(name)s',
    }
    def get_config(self, cr, uid, ids, model,context=None):
        '''
        Method use with the js to hidde or show the add google doc button 
        @return : list of configuration ids or false
        '''
        if self.pool.get('ir.attachment').search_count(cr,uid,[('url','like','https://docs.google.com/%'),('res_model','=',model),('res_id','=',ids[0])]) !=0:
            return  False
        else:
            return True
config()


