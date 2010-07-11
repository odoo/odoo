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

class crm_send_new_email2(osv.osv_memory):
    """ Sends new email for the case"""
    _name = "crm.send.mail"
    _description = "Send new email"

    _columns = {
        'email_to' : fields.char('To', size=512, required=True),
        'email_from' : fields.char('From', size=128, required=True),
        'email_cc' : fields.char('CC', size=512, help="Carbon Copy: list of recipients that will receive"\
                                    " a copy of this mail, and future communication related to this case"),
        'subject': fields.char('Subject', size=512, required=True),
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

        hist_obj = self.pool.get('mailgate.message')

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
            ref_id = None

            case = case_pool.browse(cr, uid, res_id)
            if context.get('mail', 'new') == 'new':
                if case.message_ids:
                    message_id = case.message_ids[0].message_id
            else:
                hist = hist_obj.browse(cr, uid, res_id)
                message_id = hist.message_id
                model = hist.model
                model_pool = self.pool.get(model)
                res_id = hist.res_id
                ref_id = hist.ref_id
                case = model_pool.browse(cr, uid, res_id)
            emails = [obj.email_to]
            email_cc = obj.email_cc and  obj.email_cc.split(',') or ''
            emails = filter(None, emails)
            body = obj.text

            body = case_pool.format_body(body)
            email_from = getattr(obj, 'email_from', False)
            x_headers = {}
            if message_id:
                x_headers['References'] = "%s" % (message_id)

            flag = tools.email_send(
                email_from,
                emails,
                obj.subject,
                body,
                email_cc=email_cc,
                attach=attach,
                reply_to=case.section_id and case.section_id.reply_to,
                openobject_id=str(case.id),
                x_headers=x_headers
            )

            if not flag:
                raise osv.except_osv(_('Error!'), _('Unable to send mail. Please check SMTP is configured properly.'))
            if flag:
                case_pool.history(cr, uid, [case], _('Send'), history=True, \
                                email=obj.email_to, details=body, \
                                subject=obj.subject, email_from=email_from, \
                                email_cc=email_cc, message_id=message_id, \
                                references=ref_id or message_id, attach=attach)
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

        res = super(crm_send_new_email2, self).default_get(cr, uid, fields, context=context)

        if context.get('mail') == 'reply':
            res.update(self.get_reply_defaults(cr, uid, fields, context=context))
            return res

        model = context.get('model')
        mod_obj = self.pool.get(model)
        res_id = context and context.get('active_ids', []) or []

        user_obj = self.pool.get('res.users')
        user_mail_from = user_obj._get_email_from(cr, uid, [uid], context=context)[uid]

        for case in mod_obj.browse(cr, uid, res_id):
            if 'email_to' in fields:
                res.update({'email_to': tools.ustr(case.email_from)})
            if 'email_from' in fields:
                res.update({'email_from': tools.ustr(user_mail_from)})
            if 'subject' in fields:
                res.update({'subject': tools.ustr(context.get('subject', case.name) or '')})
            if 'email_cc' in fields:
                res.update({'email_cc': tools.ustr(case.email_cc or '')})
            if 'text' in fields:
                res.update({'text': u'\n'+(tools.ustr(case.user_id.signature or ''))})
            if 'state' in fields:
                res.update({'state': u'pending'})

        return res

    def get_reply_defaults(self, cr, uid, fields, context=None):
        """
        This function gets default values for reply mail
        """
        hist_obj = self.pool.get('mailgate.message')
        res_ids = context and context.get('active_ids', []) or []

        user_obj = self.pool.get('res.users')
        user_mail_from = user_obj._get_email_from(cr, uid, [uid], context=context)[uid]

        include_original = context and context.get('include_original', False) or False
        res = {}
        for hist in hist_obj.browse(cr, uid, res_ids, context=context):
            model = hist.model

            # In the case where the crm.case does not exist in the database
            if not model:
                return {}

            model_pool = self.pool.get(model)
            res_id = hist.res_id
            case = model_pool.browse(cr, uid, res_id)
            if 'email_to' in fields:
                res.update({'email_to': case.email_from and tools.ustr(case.email_from) or False})
            if 'email_from' in fields:
                res.update({'email_from': user_mail_from and tools.ustr(user_mail_from) or False})

            signature = u'\n' + (tools.ustr(case.user_id.signature or '')) + u'\n'
            original = [signature]

            if include_original == True and 'text' in fields:
                header = u'-------- Original Message --------'
                sender = u'From: %s' %(tools.ustr(hist.email_from or ''))
                to = u'To: %s' % (tools.ustr(hist.email_to or ''))
                sentdate = u'Date: %s' % (tools.ustr(hist.date))
                desc = u'\n%s'%(tools.ustr(hist.description))

                original = [signature, header, sender, to, sentdate, desc]

            res['text']= u'\n' + u'\n'.join(original)

            if 'subject' in fields:
                res.update({u'subject': u'Re: %s' %(tools.ustr(hist.name or ''))})
            if 'state' in fields:
                res['state'] = u'pending'
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
        return True

crm_send_new_email2()

