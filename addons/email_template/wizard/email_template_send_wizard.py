# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009 Sharoon Thomas
#    Copyright (C) 2010-2010 OpenERP SA (<http://www.openerp.com>)
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
from mako.template import Template
from mako import exceptions
import netsvc
import base64
from tools.translate import _
import tools
from email_template.email_template import get_value


## FIXME: this wizard duplicates a lot of features of the email template preview,
##        one of the 2 should inherit from the other!

class email_template_send_wizard(osv.osv_memory):
    _name = 'email_template.send.wizard'
    _description = 'This is the wizard for sending mail'
    _rec_name = "subject"

    def _get_accounts(self, cr, uid, context=None):
        if context is None:
            context = {}

        template = self._get_template(cr, uid, context)
        if not template:
            return []

        logger = netsvc.Logger()

        if template.from_account:
            return [(template.from_account.id, '%s (%s)' % (template.from_account.name, template.from_account.email_id))]
        else:
            account_id = self.pool.get('email_template.account').search(cr,uid,[('company','=','no'),('user','=',uid)], context=context)
            if account_id:
                account = self.pool.get('email_template.account').browse(cr,uid,account_id, context)
                return [(r.id,r.name + " (" + r.email_id + ")") for r in account]
            else:
                logger.notifyChannel(_("email-template"), netsvc.LOG_ERROR, _("No personal email accounts are configured for you. \nEither ask admin to enforce an account for this template or get yourself a personal email account."))
                raise osv.except_osv(_("Missing mail account"),_("No personal email accounts are configured for you. \nEither ask admin to enforce an account for this template or get yourself a personal email account."))

    def get_value(self, cursor, user, template, message, context=None, id=None):
        """Gets the value of the message parsed with the content of object id (or the first 'src_rec_ids' if id is not given)"""
        if not message:
            return ''
        if not id:
            id = context['src_rec_ids'][0]
        return get_value(cursor, user, id, message, template, context)
    
    def _get_template(self, cr, uid, context=None):
        if context is None:
            context = {}
        if not 'template' in context and not 'template_id' in context:
            return None
        if 'template_id' in context.keys():
            template_ids = self.pool.get('email.template').search(cr, uid, [('id','=',context['template_id'])], context=context)
        elif 'template' in context.keys():
            # Old versions of email_template used the name of the template. This caused
            # problems when the user changed the name of the template, but we keep the code
            # for compatibility with those versions.
            template_ids = self.pool.get('email.template').search(cr, uid, [('name','=',context['template'])], context=context)
        if not template_ids:
            return None

        template = self.pool.get('email.template').browse(cr, uid, template_ids[0], context)

        lang = self.get_value(cr, uid, template, template.lang, context)
        if lang:
            # Use translated template if necessary
            ctx = context.copy()
            ctx['lang'] = lang
            template = self.pool.get('email.template').browse(cr, uid, template.id, ctx)
        return template

    def _get_template_value(self, cr, uid, field, context=None):
        if context is None:
            context = {}
        template = self._get_template(cr, uid, context)
        if not template:
            return False
        if len(context['src_rec_ids']) > 1: # Multiple Mail: Gets original template values for multiple email change
            return getattr(template, field)
        else: # Simple Mail: Gets computed template values
            return self.get_value(cr, uid, template, getattr(template, field), context)

    _columns = {
        'state':fields.selection([
                        ('single','Simple Mail Wizard Step 1'),
                        ('multi','Multiple Mail Wizard Step 1'),
                        ('done','Wizard Complete')
                                  ],'Status',readonly=True),
        'ref_template':fields.many2one('email.template','Template',readonly=True),
        'rel_model':fields.many2one('ir.model','Model',readonly=True),
        'rel_model_ref':fields.integer('Referred Document',readonly=True),
        'from':fields.selection(_get_accounts,'From Account',select=True),
        'to':fields.char('To',size=250,required=True),
        'cc':fields.char('CC',size=250,),
        'bcc':fields.char('BCC',size=250,),
        'reply_to':fields.char('Reply-To', 
                    size=250, 
                    help="The address recipients should reply to,"
                         " if different from the From address."
                         " Placeholders can be used here."),
        'message_id':fields.char('Message-ID', 
                    size=250, 
                    help="The Message-ID header value, if you need to"
                         "specify it, for example to automatically recognize the replies later."
                        " Placeholders can be used here."),
        'subject':fields.char('Subject',size=200),
        'body_text':fields.text('Body',),
        'body_html':fields.text('Body',),
        'report':fields.char('Report File Name',size=100,),
        'signature':fields.boolean('Attach my signature to mail'),
        #'filename':fields.text('File Name'),
        'requested':fields.integer('No of requested Mails',readonly=True),
        'generated':fields.integer('No of generated Mails',readonly=True), 
        'full_success':fields.boolean('Complete Success',readonly=True),
        'attachment_ids': fields.many2many('ir.attachment','send_wizard_attachment_rel', 'wizard_id', 'attachment_id', 'Attachments'),
    }

    #FIXME: probably better by overriding default_get directly 
    _defaults = {
        'state': lambda self,cr,uid,ctx: len(ctx['src_rec_ids']) > 1 and 'multi' or 'single',
        'rel_model': lambda self,cr,uid,ctx: self.pool.get('ir.model').search(cr,uid,[('model','=',ctx['src_model'])],context=ctx)[0],
        'rel_model_ref': lambda self,cr,uid,ctx: ctx['active_id'],
        'to': lambda self,cr,uid,ctx: self._get_template_value(cr, uid, 'def_to', ctx),
        'cc': lambda self,cr,uid,ctx: self._get_template_value(cr, uid, 'def_cc', ctx),
        'bcc': lambda self,cr,uid,ctx: self._get_template_value(cr, uid, 'def_bcc', ctx),
        'subject':lambda self,cr,uid,ctx: self._get_template_value(cr, uid, 'def_subject', ctx),
        'body_text':lambda self,cr,uid,ctx: self._get_template_value(cr, uid, 'def_body_text', ctx),
        'body_html':lambda self,cr,uid,ctx: self._get_template_value(cr, uid, 'def_body_html', ctx),
        'report': lambda self,cr,uid,ctx: self._get_template_value(cr, uid, 'file_name', ctx),
        'signature': lambda self,cr,uid,ctx: self._get_template(cr, uid, ctx).use_sign,
        'ref_template':lambda self,cr,uid,ctx: self._get_template(cr, uid, ctx).id,
        'reply_to': lambda self,cr,uid,ctx: self._get_template_value(cr, uid, 'reply_to', ctx),
        'reply_to': lambda self,cr,uid,ctx: self._get_template_value(cr, uid, 'reply_to', ctx),
        'requested':lambda self,cr,uid,ctx: len(ctx['src_rec_ids']),
        'full_success': False,
        'attachment_ids': [], 
    }

    def fields_get(self, cr, uid, fields=None, context=None, write_access=True):
        if context is None:
            context = {}
        result = super(email_template_send_wizard, self).fields_get(cr, uid, fields, context, write_access)
        if 'attachment_ids' in result and 'src_model' in context:
            result['attachment_ids']['domain'] = [('res_model','=',context['src_model']),('res_id','=',context['active_id'])]
        return result

    def sav_to_drafts(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mailid = self.save_to_mailbox(cr, uid, ids, context=context)
        if self.pool.get('email_template.mailbox').write(cr, uid, mailid, {'folder':'drafts'}, context):
            return {'type':'ir.actions.act_window_close' }

    def send_mail(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mailid = self.save_to_mailbox(cr, uid, ids, context)
        if self.pool.get('email_template.mailbox').write(cr, uid, mailid, {'folder':'outbox'}, context):
            return {'type':'ir.actions.act_window_close' }

    def get_generated(self, cr, uid, ids=None, context=None):
        if ids is None:
            ids = []
        if context is None:
            context = {}
        logger = netsvc.Logger()
        if context['src_rec_ids'] and len(context['src_rec_ids'])>1:
            #Means there are multiple items selected for email.
            mail_ids = self.save_to_mailbox(cr, uid, ids, context)
            if mail_ids:
                self.pool.get('email_template.mailbox').write(cr, uid, mail_ids, {'folder':'outbox'}, context)
                logger.notifyChannel("email-template", netsvc.LOG_INFO, _("Emails for multiple items saved in outbox."))
                self.write(cr, uid, ids, {
                    'generated':len(mail_ids),
                    'state':'done'
                }, context)
            else:
                raise osv.except_osv(_("Email Template"),_("Email sending failed for one or more objects."))
        return True
     
    def save_to_mailbox(self, cr, uid, ids, context=None):
        def get_end_value(id, value):
            if len(context['src_rec_ids']) > 1: # Multiple Mail: Gets value from the template
                return self.get_value(cr, uid, template, value, context, id)
            else:
                return value

        if context is None:
            context = {}
        mail_ids = []
        template = self._get_template(cr, uid, context)
        for id in context['src_rec_ids']:
            screen_vals = self.read(cr, uid, ids[0], [],context)
            account = self.pool.get('email_template.account').read(cr, uid, screen_vals['from'], context=context)
            vals = {
                'email_from': tools.ustr(account['name']) + "<" + tools.ustr(account['email_id']) + ">",
                'email_to': get_end_value(id, screen_vals['to']),
                'email_cc': get_end_value(id, screen_vals['cc']),
                'email_bcc': get_end_value(id, screen_vals['bcc']),
                'subject': get_end_value(id, screen_vals['subject']),
                'body_text': get_end_value(id, screen_vals['body_text']),
                'body_html': get_end_value(id, screen_vals['body_html']),
                'account_id': screen_vals['from'],
                'state':'na',
                'mail_type':'multipart/alternative' #Options:'multipart/mixed','multipart/alternative','text/plain','text/html'
            }
            if screen_vals['signature']:
                signature = self.pool.get('res.users').read(cr, uid, uid, ['signature'], context)['signature']
                if signature:
                    vals['body_text'] = tools.ustr(vals['body_text'] or '') + signature
                    vals['body_html'] = tools.ustr(vals['body_html'] or '') + signature

            attachment_ids = []

            #Create partly the mail and later update attachments
            mail_id = self.pool.get('email_template.mailbox').create(cr, uid, vals, context)
            mail_ids.append(mail_id)
            if template.report_template:
                reportname = 'report.' + self.pool.get('ir.actions.report.xml').read(cr, uid, template.report_template.id, ['report_name'], context)['report_name']
                data = {}
                data['model'] = self.pool.get('ir.model').browse(cr, uid, screen_vals['rel_model'], context).model

                # Ensure report is rendered using template's language
                ctx = context.copy()
                if template.lang:
                    ctx['lang'] = self.get_value(cr, uid, template, template.lang, context, id)
                service = netsvc.LocalService(reportname)
                (result, format) = service.create(cr, uid, [id], data, ctx)
                attachment_id = self.pool.get('ir.attachment').create(cr, uid, {
                    'name': _('%s (Email Attachment)') % tools.ustr(vals['subject']),
                    'datas': base64.b64encode(result),
                    'datas_fname': tools.ustr(get_end_value(id, screen_vals['report']) or _('Report')) + "." + format,
                    'description': vals['body_text'] or _("No Description"),
                    'res_model': 'email_template.mailbox',
                    'res_id': mail_id
                }, context)
                attachment_ids.append( attachment_id )

            # Add document attachments
            for attachment_id in screen_vals.get('attachment_ids',[]):
                new_id = self.pool.get('ir.attachment').copy(cr, uid, attachment_id, {
                    'res_model': 'email_template.mailbox',
                    'res_id': mail_id,
                }, context)
                attachment_ids.append( new_id )

            if attachment_ids:
                self.pool.get('email_template.mailbox').write(cr, uid, mail_id, {
                    'attachments_ids': [[6, 0, attachment_ids]],
                    'mail_type': 'multipart/mixed'
                }, context)

        return mail_ids
email_template_send_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
