'''
Created on 18 oct. 2011

@author: openerp
'''

from openerp.osv import osv
from openerp.tools.translate import _

class plugin_handler(osv.osv_memory):
    _name = 'plugin.handler'

    def _make_url(self, cr, uid, res_id, model, context=None):
        """
            @param res_id: on which document the message is pushed
            @param model: name of the document linked with the mail
            @return url
        """
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url', default='http://localhost:8069', context=context)
        if base_url:
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            base_url += '/login?db=%s&login=%s&key=%s#id=%s&model=%s' % (cr.dbname, user.login, user.password, res_id, model)
        return base_url

    def is_installed(self, cr, uid):
        return True

    def partner_get(self, cr, uid, address_email):
        partner_obj = self.pool.get('res.partner')
        partner_ids = partner_obj.search(cr, uid, [('email', 'like', address_email)])
        res_id = partner_ids and partner_ids[0] or 0
        url = self._make_url(cr, uid, res_id, 'res.partner')
        return ('res.partner', res_id, url)

    def document_get(self, cr, uid, email):
        """
            @param email: email is a standard RFC2822 email message
            @return Dictionary which contain id and the model name of the document linked with the mail
                if no document is found the id = 0
                (model_name, res_id, url, name_get)
        """
        mail_message_obj = self.pool.get('mail.message')
        model = ""
        res_id = 0
        url = ""
        name = ""
        msg = self.pool.get('mail.thread').message_parse(cr, uid, email)
        parent_id = msg.get('parent_id', False)
        message_id = msg.get('message_id')
        msg_id = False
        if message_id:
            msg_ids = mail_message_obj.search(cr, uid, [('message_id', '=', message_id)])
            msg_id = len(msg_ids) and msg_ids[0] or False
        if not msg_id and parent_id:
            msg_id = parent_id
        if msg_id:
            msg = mail_message_obj.browse(cr, uid, msg_id)
            res_id = msg.res_id
            model = msg.model
            url = self._make_url(cr, uid, res_id, model)
            name = self.pool.get(model).name_get(cr, uid, [res_id])[0][1]
        return (model, res_id, url, name)

    def document_type(self, cr, uid, context=None):
        """
            Return the list of available model to push
            res.partner is a special case
            otherwise all model that inherit from mail.thread
            ['res.partner', 'project.issue']
        """
        mail_thread_obj = self.pool.get('mail.thread')
        doc_dict = mail_thread_obj.message_capable_models(cr, uid, context)
        doc_dict['res.partner'] = "Partner"
        return doc_dict.items()

    # Can be used where search record was used
    def list_document_get(self, cr, uid, model, name):
        """
            This function return the result of name_search on the object model
            @param model: the name of the model
            @param : the name of the document
            @return : the result of name_search a list of tuple
            [(id, 'name')]
        """
        return self.pool.get(model).name_search(cr, uid, name)

    def push_message(self, cr, uid, model, email, res_id=0):
        """
            @param email: email is a standard RFC2822 email message
            @param model: On which model the message is pushed
            @param thread_id: on which document the message is pushed, if thread_id = 0 a new document is created
            @return Dictionary which contain model , url and resource id.
        """
        mail_message = self.pool.get('mail.message')
        model_obj = self.pool.get(model)
        msg = self.pool.get('mail.thread').message_parse(cr, uid, email)
        message_id = msg.get('message-id')
        mail_ids = mail_message.search(cr, uid, [('message_id', '=', message_id), ('res_id', '=', res_id), ('model', '=', model)])
        if message_id and mail_ids:
            mail_record = mail_message.browse(cr, uid, mail_ids)[0]
            res_id = mail_record.res_id
            notify = _("Email already pushed")
        elif res_id == 0:
            if model == 'res.partner':
                notify = _('Use the Partner button to create a new partner')
            else:
                res_id = model_obj.message_process(cr, uid, model, email)
                notify = _("Mail successfully pushed, a new %s has been created.") % model
        else:
            model_obj.message_post(cr, uid, [res_id],
                            body=msg.get('body'),
                            subject=msg.get('subject'),
                            type='comment' if model == 'res.partner' else 'email',
                            parent_id=msg.get('parent_id'),
                            attachments=msg.get('attachments'))
            notify = _("Mail successfully pushed")
        url = self._make_url(cr, uid, res_id, model)
        return (model, res_id, url, notify)

    def contact_create(self, cr, uid, data, partner_id, context=None):
        """
            @param data : the data use to create the res.partner
                [('field_name', value)], field name is required
            @param partner_id : On which partner the address is attached
             if partner_id = 0 then create a new partner with the same name that the address
            @return : the partner_id sended or created, this allow the plugin to open the right partner page
        """
        partner_obj = self.pool.get('res.partner')
        dictcreate = dict(data)
        if partner_id:
            is_company = partner_obj.browse(cr, uid, partner_id, context=context).is_company
            if is_company:
                dictcreate['parent_id'] = partner_id
        partner_id = partner_obj.create(cr, uid, dictcreate)
        url = self._make_url(cr, uid, partner_id, 'res.partner')
        return ('res.partner', partner_id, url)

    # Specific to outlook rfc822 is not available so we split in arguments headerd,body,attachemnts
    def push_message_outlook(self, cr, uid, model, headers, res_id=0, body=False, body_html=False, attachments=False):
        # ----------------------------------------
        # solution 1
        # construct a fake rfc822 from the separated arguement
        #m = email.asdfsadf
        # use the push_message method
        #self.push_message(m)
        # ----------------------------------------
        # solution 2
        # use self.pushmessage only with header and body
        # add attachemnt yourself after
        mail_message = self.pool.get('mail.message')
        ir_attachment_obj = self.pool.get('ir.attachment')
        attach_ids = []
        msg = self.pool.get('mail.thread').message_parse(cr, uid, headers)
        message_id = msg.get('message-id')
        push_mail = self.push_message(cr, uid, model, headers, res_id)
        res_id = push_mail[1]
        model = push_mail[0]
        notify = push_mail[3]
        for name in attachments.keys():
            attachment_ids = ir_attachment_obj.search(cr, uid, [('res_model', '=', model), ('res_id', '=', res_id), ('datas_fname', '=', name)])
            if attachment_ids:
                attach_ids.append(attachment_ids[0])
            else:
                vals = {"res_model": model, "res_id": res_id, "name": name, "datas": attachments[name], "datas_fname": name}
                attach_ids.append(ir_attachment_obj.create(cr, uid, vals))
        mail_ids = mail_message.search(cr, uid, [('message_id', '=', message_id), ('res_id', '=', res_id), ('model', '=', model)])
        if mail_ids:
            mail_message.write(cr, uid, mail_ids[0], {'attachment_ids': [(6, 0, attach_ids)], 'body': body, 'body_html': body_html})
        url = self._make_url(cr, uid, res_id, model)
        return (model, res_id, url, notify)
