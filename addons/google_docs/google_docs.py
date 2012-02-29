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

    def create_empty_gdoc(self, cr, uid, model, context=None):
        #import pdb; pdb.set_trace()
        '''Associate a copy of the gdoc identified by 'gdocs_res_id' to the current entity.
           @param cr: the current row from the database cursor.
           @param uid: the current user ID, for security checks.
           @param model: the current model name.
           @param context: a standard dictionary for contextual values.
           @return the url of the copy itself.
           @return -2 if the google_base_account hasn't been configured yet.
        '''

        if context==None:
            context={}

        client = _auth(cr, uid)
        if client == -2:
            return -2

        resource = gdata.docs.data.Resource(gdata.docs.data.DOCUMENT_LABEL)
        gdocs_resource = client.post(entry=resource, uri='https://docs.google.com/feeds/default/private/full/')
        return gdocs_resource

    def copy_gdoc(self, cr, uid, model, gdocs_resource_id, context=None):
        if context==None:
            context={}

        client = _auth(cr, uid)
        if client == -2:
            return -2

        # fetch and copy the original document
        original_resource = client.get_resource_by_id(gdocs_resource_id)
        return client.copy_resource(entry=original_resource)

    def gdoc_get(self, cr, uid, model, context=None):
        google_docs_config_ref = self.pool.get('google.docs.config')
        google_template_ids = google_docs_config_ref.search(cr, uid, [('model', '=', model)])
        if not google_template_ids:
            # there isn't any template. Create an empty doc.
            return self.create_gdoc(cr, uid, model, context)

        # otherwise, copy document from existing template
        return self.copy_gdoc(cr, uid, model, google_template_ids[0].gdocs_resource_id

class google_docs_config(osv.osv):
    _name = 'google.docs.config'

    _columns = {
        'model_id': fields.many2one('ir.model', 'Model'),
        'gdocs_resource_id': fields.char('Google resource ID', size=64),
        'name_template': fields.char('GDoc name template', size=64),
        'url': fields.char('url for the template', size=122),
    }

    _defaults = {
        'name_template': 'Google Document'
    }

    edit_url_template = 'https://docs.google.com/document/d/%s/edit'
    prefix_gdoc_id_res = DOCUMENT_LABEL + ':'


class google_docs(osv.osv):
    _name = 'google.docs'

    def doc_get(self, cr, uid, model, ids, context=None):# TODO fix logic here
        google_docs_ref = self.pool.get('ir.attachment')
        gdocs_resource_id = google_docs_ref.search(cr, uid, [('model', '=', model), ('id', 'in', ids)])
        #print gdocs_resource_id
        #print google_docs_ref.edit_url_template % (gdocs_resource_id, )
        if gdocs_resource_id:
            return google_docs_ref.edit_url_template % (gdocs_resource_id, )
        else:
            ir_attachment_res = self.pool.get('ir.attachment')
            gdocs_resource = ir_attachment_res.create_empty_gdoc(cr, uid, model, context)
            if gdocs_resource == -2:
                return gdocs_resource

            # save the reference
            gdocs_resource_id = gdocs_resource.resource_id.text[len(google_docs_ref.prefix_gdoc_id_res):]
            import pdb; pdb.set_trace()
            google_docs_ref.create(cr, uid, {
                'model_id': self.pool.get(model),
                'gdocs_resource_id': gdocs_resource_id,
                'name': gdocs_resource.title.text,
            })

            return google_docs_ref.edit_url_template % (gdocs_resource_id,)
