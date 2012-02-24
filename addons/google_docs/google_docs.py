from osv import osv, fields
import gdata.docs.data
import gdata.docs.client
from gdata.client import RequestError
from gdata.docs.service import DOCUMENT_LABEL

class google_docs(osv.osv):
    _name = 'google.docs'

    _table = 'google_docs_templates'
    _columns = {
        'id': fields.integer('ID', readonly=True),
        'model': fields.many2one('ir.model', 'Model'),
        'gdocs_res_id': fields.char('Google resource ID', size=64, translate=False)
        'name_template': fields.char('Google resource ID', size=64, translate=False)
    }

    edit_url_template = 'https://docs.google.com/Edit?docid=%s'
    prefix_gdoc_id_res = DOCUMENT_LABEL + ':'

    def copy_gdoc(self, cr, uid, model, folder=None, context=None):
        '''Associate a copy of the gdoc identified by 'gdocs_res_id' to the current entity.
           @param cr: the current row from the database cursor.
           @param uid: the current user ID, for security checks.
           @param model: the current model name.
           @param folder: folder in which to store the copy.
           @param context: a standard dictionary for contextual values.
           @return the url of the copy itself.
           @return -1 if the template hasn't been assigned yet.
           @return -2 if the google_base_account hasn't been configured yet.'''

        if context==None:
            context={}

      template_vars = {
            'db' : cr.dbname,
            'model' : model,
            'id' : id,
            'salt' : salt,
            'name' : '',
        }
            name_template = 'Sales order %s %s'

        # check template for the current model
        model_obj = self.pool.get(model)
        res_gdocs_obj = self.pool.get('google.docs')
        domain = [('model' , '=', model_obj)]
        gdoc = res_gdocs_obj.search(cr,uid,domain,context=context)
        if not gdoc: 
            return -1

        # check google_base_account
        users_obj = self.pool.get('res.users')
        user = users_obj.browse(cr, uid, [uid])[0]
        if not user.gmail_user or not user.gmail_password: 
            return -2

        # copy the document
        client = gdata.docs.client.DocsClient(source='openerp.com')
        client.ssl = True
        client.http_client.debug = False
        client.ClientLogin(user.gmail_user, user.gmail_password, client.source, service='writely')
        resource = client.get_resource_by_id(gdoc.gdocs_res_id)
        copied_resource = client.copy_resource(entry=resource, title= self.name_template % (, model))

        return self.edit_url_template % (copied_resource.resource_id.text,)

    def get_documents_list(self, cr, uid, context=None):
        '''Return the list of google documents available at the user's account.
           @param cr: the current row from the database cursor.
           @param uid: the current user ID, for security checks.
           @param context: a standard dictionary for contextual values.
           @return a list with information about the documents in form of tuples (document_name, document_resource_id).
           @return -2 if the google_base_account hasn't been configured yet.'''

        if context == None:
            context = {}

        # check google_base_account
        users_obj = self.pool.get('res.users')
        user = users_obj.browse(cr, uid, [uid])[0]
        if not user.gmail_user or not user.gmail_password: 
            return -2

        # get the documents list
        client = gdata.docs.client.DocsClient(source='openerp.com')
        client.ssl = True
        client.http_client.debug = False
        client.ClientLogin(user.gmail_user, user.gmail_password, client.source, service='writely')

        return map(lambda doc: (doc.title.text, doc.resource_id.text[len(prefix_gdoc_id_res):]), filter(lambda r: r.resource_id.text.startswith('document:'), client.get_all_resources()))


    def set_model_document_template(self, cr, uid, model, resource_id, context=None):
        '''Set the default document template for the specified model. This template doesn't have to be a google documents template itself, but just a document.
           @param cr: current row for the database cursor.
           @param uid: the current user ID, for security checks.
           @param model: the current model name.
           @param resource_id: resource_id associated to the chosen document.
           @param context: a standard dictionary for contextual values.
           @return 0 on successful execution.
           @return -2 if the google_base_account hasn't been configured yet.
           @return -3 if the given resource_id doesn't exist in the user's google docs account.
        '''

        if context == None:
            context = {}

        # check google_base_account
        users_obj = self.pool.get('res.users')
        user = users_obj.browse(cr, uid, [uid])[0]
        if not user.gmail_user or not user.gmail_password:
            return -2

        # check resource_id
        client = gdata.docs.client.DocsClient(source='openerp.com')
        client.ssl = True
        client.http_client.debug = False
        client.ClientLogin(user.gmail_user, user.gmail_password, client.source, service='writely')
        try:
            client.get_resource_by_id(resource_id)
        except RequestError:
            return -3

        # set the model document template
        model_template_id = self.create(cr, uid,
            { 'model': self.pool.get(model),
              'gdocs_res_id': resource_id
            })

        return 0


class google_docs_folder(osv.osv):
    _name = 'google.docs.folder'
    _columns = {
        'res_id': fields.char('GDocs resource id', size=64, translate=False),
    }
