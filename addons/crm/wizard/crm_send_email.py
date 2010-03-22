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

class crm_send_new_email(osv.osv_memory):
    """ Sends new email for the case"""
    _name = "crm.send.mail"
    _description = "Case Send new email"

    _columns = {
                'to' : fields.char('To', size=64, required=True),
                'cc' : fields.char('CC', size=128),
                'subject': fields.char('Subject', size=128, required=True),
                'text': fields.text('Message', required=True),
                'state': fields.selection([('done', 'Done'), ('pending', 'Pending'), ('unchanged', 'Unchanged')], string='State', required=True),
                'doc1': fields.binary("Attachment1"),
                'doc2': fields.binary("Attachment2"),
                'doc3': fields.binary("Attachment3"),
                }

    def action_cancel(self, cr, uid, ids, context=None):
        """
        Closes Phonecall to Opportunity form
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Phonecall to Opportunity's IDs
        @param context: A standard dictionary for contextual values
        """
        return {'type':'ir.actions.act_window_close'}

    def action_send(self, cr, uid, ids, context=None):
        """ This sends an email to ALL the addresses of the selected partners.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Phonecall to Opportunity's IDs
        @param context: A standard dictionary for contextual values
        """
        if not context:
            context = {}

        if not context.get('model'):
            raise osv.except_osv(_('Error'), _('Can not send mail!'))

        model = context.get('model')
        case_pool = self.pool.get(model)
        res_id = context and context.get('active_id', False) or False

        for data in self.read(cr, uid, ids, context=context):
            attach = filter(lambda x: x, [data['doc1'], data['doc2'], data['doc3']])
            attach = map(lambda x: x and ('Attachment'+str(attach.index(x)+1), base64.decodestring(x)), attach)

            if context.get('mail', 'new') == 'new':
                case = case_pool.browse(cr, uid, res_id)
            else:
                hist_obj = self.pool.get('crm.case.history')
                hist = hist_obj.browse(cr, uid, res_id)
                model = hist.log_id.model_id.model
                model_pool = self.pool.get(model)
                case = model_pool.browse(cr, uid, hist.log_id.res_id)
            emails = [data['to']] + (data['cc'] or '').split(',')
            emails = filter(None, emails)
            body = data['text']

            if case.user_id.signature:
                body += '\n\n%s' % (case.user_id.signature)

            case_pool._history(cr, uid, [case], _('Send'), history=True, email=data['to'], details=body)
            email_from = (case.user_id and case.user_id.address_id and \
                            case.user_id.address_id.email) or tools.config.get('email_from',False)
            flag = tools.email_send(
                email_from,
                emails,
                data['subject'],
                case_pool.format_body(body),
                attach=attach,
                reply_to=case.section_id.reply_to,
                openobject_id=str(case.id),                
            )           
            if flag:
                if data['state'] == 'unchanged':
                    pass
                elif data['state'] == 'done':
                    case_pool.case_close(cr, uid, [case.id])
                elif data['state'] == 'pending':
                    case_pool.case_pending(cr, uid, [case.id])
                cr.commit()

#            Commented because form does not close due to raise
#                raise osv.except_osv(_('Email!'), ("Email Successfully Sent"))
#            else:
#                raise osv.except_osv(_('Warning!'), _("Email not sent !"))
        return {}

    def default_get(self, cr, uid, fields, context=None):
        """
        This function gets default values
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param fields: List of fields for default value
        @param context: A standard dictionary for contextual values

        @return : default values of fields.
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
            if 'to' in fields:
                res.update({'to': case.email_from})
            if 'subject' in fields:
                res.update({'subject': case.name})
            if 'cc' in fields:
                res.update({'cc': case.email_cc or ''})
            if 'text' in fields:
                res.update({'text': case.description or ''})
            if 'state' in fields:
                res.update({'state': 'pending'})
        return res

    def get_reply_defaults(self, cr, uid, fields, context=None):
        """
        This function gets default values for reply mail
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param fields: List of fields for default value
        @param context: A standard dictionary for contextual values

        @return : default values of fields.
        """
        hist_obj = self.pool.get('crm.case.history')
        res_ids = context and context.get('active_ids', []) or []
        res = {}
        for hist in hist_obj.browse(cr, uid, res_ids):
            model = hist.log_id.model_id.model
            model_pool = self.pool.get(model)
            case = model_pool.browse(cr, uid, hist.log_id.res_id)
            if 'to' in fields and hist.email:
                res.update({'to': hist.email})
            if 'text' in fields:
                header = '-------- Original Message --------'                
                sender = 'From: %s' %(hist.email_from or tools.config.get('email_from',False))                
                to = 'To: %s' % (hist.email)
                sentdate = 'Sent: %s' % (hist.date)
                desc = '\n%s'%(hist.description)
                original = [header, sender, to, sentdate, desc]
                original = '\n'.join(original)
                res.update({'text': '\n\n%s'%(original)})
            if 'subject' in fields:
                res.update({'subject': '[%s] %s' %(str(case.id), case.name or '')}) 
            #if 'state' in fields:
            #    res.update({'state': 'pending'})       
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
        for case in mod_obj.browse(cr, uid, context.get('active_ids', [])):
            if not case.user_id:
                raise osv.except_osv(_('Error'), _('You must define a responsible user for this case in order to use this action!'))
            if not case.user_id.address_id.email:
                raise osv.except_osv(_('Warning!'), _("Please specify user's email address !"))

        return True

crm_send_new_email()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
