# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-Today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from osv import osv
from osv import fields
import tools

class email_compose_message(osv.osv_memory):
    _name = 'email.compose.message'
    _inherit = 'email.message.template'
    _description = 'This is the wizard for Compose E-mail'

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        result = super(email_compose_message, self).default_get(cr, uid, fields, context=context)
        message_pool = self.pool.get('email.message')
        message_id = context.get('message_id', False)
        if message_id:
            message_data = message_pool.browse(cr, uid, int(message_id), context)
            if 'message_id' in fields:
                result['message_id'] =  message_data and message_data.message_id

            if 'attachment_ids' in fields:
                result['attachment_ids'] = message_data and message_pool.read(cr, uid, message_id, ['attachment_ids'])['attachment_ids']

            if 'res_id' in fields:
                result['res_id'] = message_data and message_data.res_id

            if 'email_from' in fields:
                result['email_from'] = message_data and message_data.email_to

            if 'email_to' in fields:
                result['email_to'] = message_data and message_data.email_from

            if 'email_cc' in fields:
                result['email_cc'] = message_data and message_data.email_cc

            if 'email_bcc' in fields:
                result['email_bcc'] = message_data and message_data.email_bcc

            if 'name' in fields:
                result['name']  = tools.ustr(message_data and message_data.name or '')
                if context.get('mail','') == 'reply':
                    result['name'] = "Re :- " + result['name']

            if 'description' in fields:
                description =  message_data and message_data.description and message_data.description or ''
                if context.get('mail','') == 'reply':
                    header = '-------- Original Message --------'
                    sender = 'From: %s'  % tools.ustr(message_data.email_from or '')
                    email_to = 'To: %s' %  tools.ustr(message_data.email_to or '')
                    sentdate = 'Date: %s' % message_data.date
                    desc = '\n > \t %s' % tools.ustr(description.replace('\n', "\n > \t") or '')
                    result['description'] = '\n'.join([header, sender, email_to, sentdate, desc])
                else:
                    result['description'] = description

            if 'reply_to' in fields:
                result['reply_to'] = message_data and message_data.reply_to

            if 'model' in fields:
                result['model'] = message_data and message_data.model

            if 'user_id' in fields:
                result['user_id'] = message_data and message_data.user_id and message_data.user_id.id or False

            if 'references' in fields:
                result['references'] = message_data and message_data.references and tools.ustr(message_data.references)

            if 'sub_type' in fields:
                result['sub_type'] = message_data and message_data.sub_type

            if 'headers' in fields:
                result['headers'] = message_data and message_data.headers

            if 'priority' in fields:
                result['priority'] = message_data and message_data.priority

            if 'debug' in fields:
                result['debug'] = message_data and message_data.debug

        if 'model' in fields and context.get('email_model',False):
            result['model'] = context.get('email_model')

        return result

    def _get_records(self, cr, uid, context=None):
        """
        Return Records of particular  Model
        """
        if context is None:
            context = {}
        record_ids = []
        model_pool = False
        if context.get('message_id'):
            message_pool = self.pool.get('email.message')
            message_data = message_pool.browse(cr, uid, int(context.get('message_id')), context)
            model_pool =  self.pool.get(message_data.model)
            record_ids = [message_data.res_id]
        elif context.get('email_model',False):
            model =  context.get('email_model')
            model_pool =  self.pool.get(model)
            record_ids = context.get('active_ids',[])
            if not record_ids:
                record_ids = model_pool.search(cr, uid, [])
        if model_pool:
            return model_pool.name_get(cr, uid, record_ids, context)
        return []

    _columns = {
        'attachment_ids': fields.many2many('ir.attachment','email_message_send_attachment_rel', 'wizard_id', 'attachment_id', 'Attachments'),
        'debug':fields.boolean('Debug', readonly=True),
        'res_id':fields.selection(_get_records, 'Referred Document'),
    }

    def on_change_referred_doc(self, cr, uid, ids, model, resource_id, context=None):
        return {'value':{}}

    def save_to_drafts(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        email_id = self.save_to_mailbox(cr, uid, ids, context=context)
        self.pool.get('email.message').write(cr, uid, email_id, {'folder':'drafts', 'state': 'draft'}, context)
        return {'type': 'ir.actions.act_window_close'}

    def send_mail(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        email_id = self.save_to_mailbox(cr, uid, ids, context)
        return {'type': 'ir.actions.act_window_close'}

    def save_to_mailbox(self, cr, uid, ids, context=None):
        email_ids = []
        email_message_pool = self.pool.get('email.message')
        attachment = []
        for mail in self.browse(cr, uid, ids, context=context):
            for attach in mail.attachment_ids:
                attachment.append((attach.datas_fname, attach.datas))
            references = False
            message_id = False
            if context.get('mail',False) == 'reply' and  mail.message_id:
                references = mail.references and mail.references + "," + mail.message_id or mail.message_id
            else:
                message_id = mail.message_id
            email_id = email_message_pool.email_send(cr, uid, mail.email_from, mail.email_to, mail.name, mail.description,
                    model=mail.model, email_cc=mail.email_cc, email_bcc=mail.email_bcc, reply_to=mail.reply_to,
                    attach=attachment, message_id=message_id, references=references, openobject_id=int(mail.res_id), debug=mail.debug,
                    subtype=mail.sub_type, x_headers=mail.headers, priority=mail.priority, smtp_server_id=mail.smtp_server_id and mail.smtp_server_id.id, context=context)
            email_ids.append(email_id)
        return email_ids

email_compose_message()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
