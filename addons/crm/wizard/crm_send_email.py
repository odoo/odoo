# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv, fields
from tools.translate import _
import base64
import tools
from crm import crm

class crm_send_new_email(osv.osv_memory):
    """ Sends new email for the case"""
    _name = "crm.send.mail"

crm_send_new_email()

class crm_send_new_email_attachment(osv.osv_memory):
    _name = 'crm.send.mail.attachment'

    _columns = {
        'binary' : fields.binary('Attachment', required=True),
        'name' : fields.char('Name', size=128, required=True),

        'wizard_id' : fields.many2one('crm.send.mail', 'Wizard', required=True),
    }

crm_send_new_email_attachment()

class crm_send_new_email(osv.osv_memory):
    """ Sends new email for the case"""
    _name = "crm.send.mail"
    _description = "Send new email"

    _columns = {
        'email_to' : fields.char('To', size=64, required=True),
        'email_from' : fields.char('From', size=64, required=True),
        'email_cc' : fields.char('CC', size=128),
        'subject': fields.char('Subject', size=128, required=True),
        'text': fields.text('Message', required=True),
        'state': fields.selection(crm.AVAILABLE_STATES, string='Set New State To', required=True),

        'attachment_ids' : fields.one2many('crm.send.mail.attachment', 'wizard_id'),
    }

    def action_cancel(self, cr, uid, ids, context=None):
        """ Closes Phonecall to Opportunity form
        """
        return {'type':'ir.actions.act_window_close'}

    def action_send(self, cr, uid, ids, context=None):
        """ This sends an email to ALL the addresses of the selected partners.
        """

        hist_obj = self.pool.get('crm.case.history')
        smtp_pool = self.pool.get('email.smtpclient')

        if not context:
            context = {}

        if not context.get('model'):
            raise osv.except_osv(_('Error'), _('Can not send mail!'))

        model = context.get('model')
        case_pool = self.pool.get(model)
        res_id = context and context.get('active_id', False) or False

        for obj in self.browse(cr, uid, ids, context=context):
            attach = [
                (x.name, base64.decodestring(x.binary)) for x in obj.attachment_ids
            ]

            message_id = None

            case = case_pool.browse(cr, uid, res_id)
            if context.get('mail', 'new') == 'new':
                if len(case.history_line):
                    message_id = case.history_line[0].message_id
            else:
                hist = hist_obj.browse(cr, uid, res_id)
                message_id = hist.message_id
                model = hist.log_id.model_id.model
                model_pool = self.pool.get(model)
                case = model_pool.browse(cr, uid, hist.log_id.res_id)
            emails = [obj.email_to] + (obj.email_cc or '').split(',')
            emails = filter(None, emails)
            body = obj.text

            body = case_pool.format_body(body)
            email_from = getattr(obj, 'email_from', False)
            case_pool._history(cr, uid, [case], _('Send'), history=True, email=obj.email_to, details=body, email_from=email_from, message_id=message_id)

            x_headers = dict()
            #x_headers = {
            #    'Reply-To':"%s" % case.section_id.reply_to,
            #}
            if message_id:
                x_headers['References'] = "%s" % (message_id)

            flag = False
            if case.section_id and case.section_id.server_id:
                flag = smtp_pool.send_email(
                    cr=cr,
                    uid=uid, 
                    server_id=case.section_id.server_id.id,
                    emailto=emails,
                    subject=obj.subject,
                    body="<pre>%s</pre>" % body,
                    attachments=attach,
                    headers=x_headers
                )
            else:
                flag = tools.email_send(
                    email_from,
                    emails,
                    obj.subject,
                    body,
                    attach=attach,
                    reply_to=case.section_id.reply_to,
                    openobject_id=str(case.id),
                    x_headers=x_headers
                )
            
            if flag:
                if obj.state == 'unchanged':
                    pass
                elif obj.state == 'done':
                    case_pool.case_close(cr, uid, [case.id])
                elif obj.state == 'draft':
                    case_pool.case_reset(cr, uid, [case.id])
                elif obj.state in ['cancel', 'open', 'pending']:
                    act = 'case_' + obj.state
                    getattr(case_pool, act)(cr, uid, [case.id])
                cr.commit()

        return {}

    def default_get(self, cr, uid, fields, context=None):
        """
        This function gets default values
        """
        if not context:
            context = {}

        if not context.get('model'):
            raise osv.except_osv(_('Error'), _('Can not send mail!'))

        res = super(crm_send_new_email, self).default_get(cr, uid, fields, context=context)

        if context.get('mail') == 'reply':
            res.update(self.get_reply_defaults(cr, uid, fields, context=context))
            return res

        model = context.get('model')
        mod_obj = self.pool.get(model)
        res_id = context and context.get('active_ids', []) or []

        for case in mod_obj.browse(cr, uid, res_id):
            if 'email_to' in fields:
                res.update({'email_to': case.email_from})
            if 'email_from' in fields:
                res.update({'email_from': (case.section_id and case.section_id.reply_to) or \
                            (case.user_id and case.user_id.address_id and \
                             case.user_id.address_id.email and \
                             "%s <%s>" % (case.user_id.name, case.user_id.address_id.email)) or \
                            tools.config.get('email_from',False)})
            if 'subject' in fields:
                res.update({'subject': '[%s] %s' %(str(case.id), case.name or '')})
            if 'email_cc' in fields:
                res.update({'email_cc': case.email_cc or ''})
            if 'text' in fields:
                res.update({'text': '\n\n'+(case.user_id.signature or '')})
            if 'state' in fields:
                res.update({'state': 'pending'})
        return res

    def get_reply_defaults(self, cr, uid, fields, context=None):
        """
        This function gets default values for reply mail
        """
        hist_obj = self.pool.get('crm.case.history')
        res_ids = context and context.get('active_ids', []) or []

        include_original = context and context.get('include_original', False) or False
        res = {}
        for hist in hist_obj.browse(cr, uid, res_ids):
            model = hist.log_id.model_id.model
            model_pool = self.pool.get(model)
            case = model_pool.browse(cr, uid, hist.log_id.res_id)
            if 'email_to' in fields:
                res.update({'email_to': case.email_from or hist.email_from or False})
            if 'email_from' in fields:
                res.update({'email_from': (case.section_id and case.section_id.reply_to) or \
                            (case.user_id and case.user_id.address_id and \
                            case.user_id.address_id.email) or hist.email_to or tools.config.get('email_from',False)})

            if include_original == True and 'text' in fields:
                header = '-------- Original Message --------'
                sender = 'From: %s' %(hist.email_from or '')
                to = 'To: %s' % (hist.email_to or '')
                sentdate = 'Date: %s' % (hist.date)
                desc = '\n%s'%(hist.description)
                original = [header, sender, to, sentdate, desc]
                original = '\n'.join(original)
                res['text']=original
            if 'subject' in fields:
                res.update({'subject': '[%s] %s' %(str(case.id), case.name or '')})
            if 'state' in fields:
                res['state']='pending'
        return res

    def view_init(self, cr, uid, fields_list, context=None):
        """
        This function checks for precondition before wizard executes
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param fields: List of fields for default value
        @param context: A standard dictionary for contextual values

        """
        if not context:
            context = {}

        if not context.get('model'):
            raise osv.except_osv(_('Error'), _('Can not send mail!'))
        model = context.get('model')
        mod_obj = self.pool.get(model)
        if context.get('mail') == 'reply':
            return True
        if tools.config.get('email_from'):
            return True

        for case in mod_obj.browse(cr, uid, context.get('active_ids', [])):
            if not case.user_id:
                raise osv.except_osv(_('Error'), _('You must define a responsible user for this case in order to use this action!'))
            if not case.user_id.address_id.email:
                raise osv.except_osv(_('Warning!'), _("Please specify user's email address !"))

        return True

crm_send_new_email()

