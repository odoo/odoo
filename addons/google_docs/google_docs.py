from osv import osv, fields
import gdata.docs.data
import gdata.docs.client
from gdata.client import RequestError
from gdata.docs.service import DOCUMENT_LABEL

class google_docs_config(osv.osv):
    _name = 'google.docs.config'
    _inherit = 'ir.attachment'

    _columns = {
        'model': fields.many2one('ir.model', 'Model'),
        'gdocs_resource_id': fields.char('Google resource ID', size=64),
        'name_template': fields.char('GDoc name template', size=64)
    }

    _defaults = {
        'name_template': 'Google Document'
    }

    edit_url_template = 'https://docs.google.com/document/d/%s/edit'
    prefix_gdoc_id_res = DOCUMENT_LABEL + ':'

    def copy_gdoc(self, cr, uid, model, context=None):
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

        name_template = 'Sales order %s'

        # check google_base_account
        users_obj = self.pool.get('res.users')
        user = users_obj.browse(cr, uid, [uid])[0]
        if not user.gmail_user or not user.gmail_password: 
            return -2

        # create the document
        client = gdata.docs.client.DocsClient(source='openerp.com')
        client.ssl = True
        client.http_client.debug = False
        client.ClientLogin(user.gmail_user, user.gmail_password, client.source, service='writely')
        resource = gdata.docs.data.Resource(gdata.docs.data.DOCUMENT_LABEL)
        gdocs_resource = client.post(entry=resource, uri='https://docs.google.com/feeds/default/private/full/')
        return gdocs_resource

class google_docs(osv.osv):
    _name = 'google.docs'

    def doc_get(self, cr, uid, model, ids, context=None):
        google_docs_ref = self.pool.get('google.docs.config')
        gdocs_resource_id = google_docs_ref.search(cr, uid, [('model', '=', model), ('id', 'in', ids)])
        #print gdocs_resource_id
        #print google_docs_ref.edit_url_template % (gdocs_resource_id, )
        #import pdb; pdb.set_trace()
        if gdocs_resource_id:
            return google_docs_ref.edit_url_template % (gdocs_resource_id, )
        else:
            gdocs_resource = google_docs_ref.copy_gdoc(cr, uid, model, context)
            if gdocs_resource == -2:
                return gdocs_resource

            # save the reference
            gdocs_resource_id = gdocs_resource.resource_id.text[len(google_docs_ref.prefix_gdoc_id_res):]
            google_docs_ref.create(cr, uid, {
                'model': model,
                'google_resource_id': gdocs_resource_id,
                'name': gdocs_resource_title.text,
            })

            return google_docs_ref.edit_url_template % (gdocs_resource_id,)
