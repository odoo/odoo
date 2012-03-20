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
    import gdata.docs.service
    import webbrowser
except ImportError:
    raise osv.except_osv(_('Google Docs Error!'), _('Please install gdata-python-client from http://code.google.com/p/gdata-python-client/downloads/list'))

class google_docs_ir_attachment(osv.osv):
    _inherit = 'ir.attachment'

    def _auth(self, cr, uid,context=None):
        # check google_base_account
        users_obj = self.pool.get('res.users')
        user = users_obj.browse(cr, uid, [uid])[0]
        if not user.gmail_user or not user.gmail_password:
            return False

        # login
        client = gdata.docs.client.DocsClient(source='openerp.com')
        client.ssl = True
        client.http_client.debug = False
        client.ClientLogin(user.gmail_user, user.gmail_password, client.source, service='writely') #authentification in a gmail account
        
        return client

    def create_empty_google_doc(self, cr, uid, model, ids, type_doc,context=None):
        '''Associate a copy of the gdoc identified by 'gdocs_res_id' to the current entity.
           @param cr: the current row from the database cursor.
           @param uid: the current user ID, for security checks.
           @param model: the current model name.
           @param type_doc: text, spreadsheet or slide.
           @return the document object.
           @return False if the google_base_account hasn't been configured yet.
        '''
        
        # authenticate

        '''
        client = self._auth(cr, uid)
        if client == False:
            return False
        '''
        client = self.pool.get('google.oauth')
        client.login(cr,uid,ids,context=context)

        # create the document in google docs
        if type_doc=='slide':
            local_resource = gdata.docs.data.Resource(gdata.docs.data.PRESENTATION_LABEL)
        elif type_doc=='spreadsheet':
            local_resource = gdata.docs.data.Resource(gdata.docs.data.SPREADSHEET_LABEL)
        else:
            local_resource = gdata.docs.data.Resource(gdata.docs.data.DOCUMENT_LABEL)
       
       #create a new doc in Google Docs 
        gdocs_resource = client.Post(entry=local_resource, uri='https://docs.google.com/feeds/default/private/full/')

        # register into the db
        self.create(cr, uid, {
            'res_model': model,
            'res_id': ids[0],
            'type': 'url',
            'name': 'new_foo %s' % (type_doc,) , # TODO pending from the working config
            'url': gdocs_resource.get_alternate_link().href
        },context=context)
        
        
        return gdocs_resource

    def copy_gdoc(self, cr, uid, model, ids,context=None):
        client = self._auth(cr, uid)
        if client == False:
            return False
        # fetch and copy the original document
        original_resource = client.get_resource_by_id(gdocs_resource_id)
        copy_resource = client.copy_resource(entry=original_resource)
        
        # register into the db
        self.create(cr, uid, {
            'res_model': model,
            'res_id': ids[0],
            'type': 'url',
            'name': 'file_name',
            'name': 'copy_foo %s' (type_doc,) ,  #TODO pending from the working config
            'url': copy_resource.get_alternate_link().href
        },context=context)

        return copy_resource

class google_docs(osv.osv):
    _name = 'google.docs'

    def doc_get(self, cr, uid, model, id, type_doc):
        ir_attachment_ref = self.pool.get('ir.attachment')
        google_docs_config = self.pool.get('google.docs.config').search(cr, uid, [('context_model_id', '=', model)])

        if google_docs_config:
            google_document = ir_attachment_ref.copy_gdoc(cr, uid, model, id)
        else:
            google_document = ir_attachment_ref.create_empty_google_doc(cr, uid, model, id, type_doc)
            return -1


class config(osv.osv):
    _name = 'google.docs.config'
    _description = "Google Docs templates config"

    _columns = {
        'context_model_id': fields.many2one('ir.model', 'Model'),
        'context_gdocs_resource_id': fields.char('Google resource ID', size=64,help='This is the id of the template document you kind find it in the URL'),
        'context_name_template': fields.char('GDoc name template ', size=64, help='This is the name which appears on google side'),
        'context_name': fields.char('Name', size=64, help='This is the attachment\'s name. As well, it appears on the panel.'),
        'context_multiple': fields.boolean('Multiple documents')
    }

    _defaults = {
        'context_name_template': 'Google Document',
        'context_name': 'pr_%(name)',
        'context_multiple': False,
    }
    def get_config(self, cr, uid, model):
        domain = [('context_model_id', '=', model)]
        if self.search_count(cr, uid, domain) != 0:
            return False
        else:
            return self.search(cr, uid, domain)
config()



class oauth (osv.osv):
    _name = 'google.oauth'
    def login(self,cr,uid,ids,context=None):
        consumer_key = '751376579939.apps.googleusercontent.com'
        consumer_secret = '_KGpgyO8DZIseyG3N-j-h8gN'
        gd_client = gdata.docs.service.DocsService()
        #Set OAuth input parameters
        gd_client.SetOAuthInputParameters(gdata.auth.OAuthSignatureMethod.HMAC_SHA1,consumer_key, consumer_secret=consumer_secret)
        #Fetch OAuth Request token
        request_token = gd_client.FetchOAuthRequestToken()
        #Set the fetched OAuth token
        gd_client.SetOAuthToken(request_token)
        #Generate OAuth authorization URL
        auth_url = gd_client.GenerateOAuthAuthorizationURL()
        webbrowser.open(auth_url)
        print gd_client.SetOAuthToken(request_token) 
        consumer_key = raw_input('Please enter consumer key: ')

        #Upgrade to an OAuth access token
        gd_client.UpgradeToOAuthAccessToken()
        #Access Token
        gd_client.token_store.find_token(request_token.scopes[0])
