# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009 Sharoon Thomas
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

from osv import osv, fields
import netsvc
from tools.translate import _

class email_template_send_wizard(osv.osv_memory):
    _name = 'email_template.send.wizard'
    _inherit = 'email.template'
    _description = 'This is the wizard for sending mail'

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        result = super(email_template_send_wizard, self).default_get(cr, uid, fields, context=context)

        template_pool = self.pool.get('email.template')
        model_pool = self.pool.get('ir.model')
        template_id=context.get('template_id', False)
        template = template_pool.get_email_template(cr, uid, template_id=template_id, context=context)
        def _get_template_value(field):
            if not template:
                return False
            if len(context['src_rec_ids']) > 1: # Multiple Mail: Gets original template values for multiple email change
                return getattr(template, field)
            else: # Simple Mail: Gets computed template values
                return self.get_template_value(cr, uid, getattr(template, field), template.model, context.get('active_id'), context)

        if 'user_signature' in fields:
            result['user_signature'] = template.user_signature

        if 'report_template' in fields:
            result['report_template'] = template.report_template and template.report_template.id or False

        if 'template_id' in fields:
            result['template_id'] = template.id

        if 'smtp_server_id' in fields:
            result['smtp_server_id'] = template.smtp_server_id.id

        if 'message_id' in fields:
            result['message_id'] = template.message_id

        if 'track_campaign_item' in fields:
            result['track_campaign_item'] = template.track_campaign_item

        if 'attachment_ids' in fields:
            result['attachment_ids'] = template_pool.read(cr, uid, template.id, ['attachment_ids'])['attachment_ids']

        if 'requested' in fields:
            result['requested'] = len(context.get('src_rec_ids',''))

        if 'state' in fields:
            result['state'] =  len(context.get('src_rec_ids','')) > 1 and 'multi' or 'single'

        if 'model_id' in fields:
            result['model_id'] = model_pool.search(cr, uid, [('model','=',context.get('src_model'))],context=context)[0]

        if 'res_id' in fields:
            result['res_id'] = context['active_id']

        if 'email_to' in fields:
            result['email_to'] = _get_template_value('email_to')

        if 'email_cc' in fields:
            result['email_cc'] = _get_template_value('email_cc')

        if 'email_bcc' in fields:
            result['email_bcc'] = _get_template_value('email_bcc')

        if 'subject' in fields:
            result['subject'] = _get_template_value('subject')

        if 'description' in fields:
            result['description'] = _get_template_value('description')

        #if 'body_html' in fields:
        #    result['body_html'] = _get_template_value('body_html')

        if 'reply_to' in fields:
            result['reply_to'] = _get_template_value('reply_to')

        if 'report_name' in fields:
            result['report_name'] = _get_template_value('report_name')

        return result

    _columns = {
        'requested':fields.integer('No of requested Mails',readonly=True),
        'generated':fields.integer('No of generated Mails',readonly=True),
        'full_success':fields.boolean('Complete Success',readonly=True),
        'attachment_ids': fields.many2many('ir.attachment','send_wizard_attachment_rel', 'wizard_id', 'attachment_id', 'Attachments'),
        'state':fields.selection([
                        ('single','Simple Mail Wizard Step 1'),
                        ('multi','Multiple Mail Wizard Step 1'),
                        ('done','Wizard Complete')
                                  ],'State',readonly=True),
    }

    _defaults = {
    }

    #def fields_get(self, cr, uid, fields=None, context=None, write_access=True):
    #    if context is None:
    #        context = {}
    #    result = super(email_template_send_wizard, self).fields_get(cr, uid, fields, context, write_access)
    #    if 'attachment_ids' in result and 'src_model' in context:
    #        result['attachment_ids']['domain'] = [('res_model','=',context['src_model']),('res_id','=',context['active_id'])]
    #    return result

    def save_to_drafts(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mailid = self.save_to_mailbox(cr, uid, ids, context=context)
        self.pool.get('email.message').write(cr, uid, mailid, {'folder':'drafts', 'state': 'draft'}, context)
        return {'type': 'ir.actions.act_window_close'}

    def send_mail(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mailid = self.save_to_mailbox(cr, uid, ids, context)
        return {'type': 'ir.actions.act_window_close'}

    def get_generated(self, cr, uid, ids=None, context=None):
        if ids is None:
            ids = []
        if context is None:
            context = {}
        logger = netsvc.Logger()
        if context.get('src_rec_ids'):
            #Means there are multiple items selected for email.
            mail_ids = self.save_to_mailbox(cr, uid, ids, context)
            if mail_ids:
                logger.notifyChannel("email-template", netsvc.LOG_INFO, _("Emails for multiple items saved in outbox."))
                self.write(cr, uid, ids, {
                    'generated':len(mail_ids),
                    'state':'done'
                }, context)
            else:
                raise osv.except_osv(_("Email Template"),_("Email sending failed for one or more objects."))
        return True

    def save_to_mailbox(self, cr, uid, ids, context=None):
        #def get_end_value(id, value):
        #    if len(context['src_rec_ids']) > 1: # Multiple Mail: Gets value from the template
        #        return self.get_value(cr, uid, template, value, context, id)
        #    else:
        #        return value

        email_ids = []
        for template in self.browse(cr, uid, ids, context=context):
            for record_id in context.get('src_rec_ids',[]):
                email_id = self._generate_email(cr, uid, template.id, record_id, context)
                email_ids.append(email_id)
        return email_ids

email_template_send_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
