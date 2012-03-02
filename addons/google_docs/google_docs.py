from osv import osv, fields
import gdata.docs.data
import gdata.docs.client
from gdata.client import RequestError
from gdata.docs.service import DOCUMENT_LABEL

class google_docs_ir_attachment(osv.osv):
    _inherit = 'ir.attachment'

    def _auth(self, cr, uid):
        # check google_base_account
        users_obj = self.pool.get('res.users')
        user = users_obj.browse(cr, uid, [uid])[0]
        if not user.gmail_user or not user.gmail_password: 
            return -2

        # login
        client = gdata.docs.client.DocsClient(source='openerp.com')
        client.ssl = True
        client.http_client.debug = False
        client.ClientLogin(user.gmail_user, user.gmail_password, client.source, service='writely')
        
        return client

    def create_empty_google_doc(self, cr, uid, model, ids, type_doc):
        '''Associate a copy of the gdoc identified by 'gdocs_res_id' to the current entity.
           @param cr: the current row from the database cursor.
           @param uid: the current user ID, for security checks.
           @param model: the current model name.
           @param type_doc: text, spreadsheet or slide.
           @return the document object.
           @return -2 if the google_base_account hasn't been configured yet.
        '''

        # authenticate
        client = self._auth(cr, uid)
        if client == -2:
            return -2

        # create the document in google docs
        if type_doc=='slide':
            local_resource = gdata.docs.data.Resource(gdata.docs.data.PRESENTATION_LABEL)
        elif type_doc=='spreadsheet':
            local_resource = gdata.docs.data.Resource(gdata.docs.data.SPREADSHEET_LABEL)
        else:
            local_resource = gdata.docs.data.Resource(gdata.docs.data.DOCUMENT_LABEL)
        gdocs_resource = client.post(entry=local_resource, uri='https://docs.google.com/feeds/default/private/full/')

        # register into the db
        self.create(cr, uid, {
            'res_model': model,
            'res_id': ids[0],
            'type': 'url',
            'name': 'new_foo %s' % (type_doc,) , # TODO pending from the working config
            'url': gdocs_resource.get_alternate_link().href
        })

        return gdocs_resource

    def copy_gdoc(self, cr, uid, model, ids):
        if context is None:
            context={}

        client = self._auth(cr, uid)
        if client == -2:
            return -2

        # fetch and copy the original document
        original_resource = client.get_resource_by_id(gdocs_resource_id)
        copy_resource = client.copy_resource(entry=original_resource)

        # register into the db
        self.create(cr, uid, {
            'res_model': model,
            'res_id': ids[0],
            'type': 'url',
            'name': 'copy_foo %s' (type_doc,) , # TODO pending from the working config
            'url': copy_resource.get_alternate_link().href
        })

        return copy_resource

class google_docs_config(osv.osv):
    _name = 'google.docs.config'

    _columns = {
        'model_id': fields.many2one('ir.model', 'Model'),
        'gdocs_resource_id': fields.char('Google resource ID', size=64),
        'name_template': fields.char('GDoc name template ', size=64, help='This is the name which appears on google side'),
        'name': fields.char('Name', size=64, help='This is the attachment\'s name. As well, it appears on the panel.')
        # 'multi': fields.boolean('Multiple documents')
    }

    _defaults = {
        'name_template': 'Google Document'
    }



class google_docs(osv.osv):
    _name = 'google.docs'

    def doc_get(self, cr, uid, model, id, type_doc):# TODO fix logic here
        google_docs_config_ref = self.pool.get('google.docs.config')
        ir_attachment_ref = self.pool.get('ir.attachment')
        google_docs_config = google_docs_config_ref.search(cr, uid, [('model_id', '=', model)])

        if not google_docs_config:
            google_document = ir_attachment_ref.create_empty_google_doc(cr, uid, model, id, type_doc)
        else:
            google_document = ir_attachment_ref.copy_gdoc(cr, uid, model, id)

        print google_docs_config

        if not google_docs_config:
            return -1

