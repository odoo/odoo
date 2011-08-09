# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import re
import tools

from tools.translate import _
from osv import fields
from osv import osv

import crm

class base_action_rule(osv.osv):
    """ Base Action Rule """
    _inherit = 'base.action.rule'
    _description = 'Action Rules'

    _columns = {
        'trg_section_id': fields.many2one('crm.case.section', 'Sales Team'),
        'trg_max_history': fields.integer('Maximum Communication History'),
        'trg_categ_id':  fields.many2one('crm.case.categ', 'Category'),
        'regex_history' : fields.char('Regular Expression on Case History', size=128),
        'act_section_id': fields.many2one('crm.case.section', 'Set Team to'),
        'act_categ_id': fields.many2one('crm.case.categ', 'Set Category to'),
        'act_mail_to_partner': fields.boolean('Mail to Partner',
                                              help="Check this if you want the rule to send an email to the partner."),
    }

    def email_send(self, cr, uid, obj, emails, body, emailfrom=tools.config.get('email_from', False), context=None):
        mail_message = self.pool.get('mail.message')
        body = self.format_mail(obj, body)
        if not emailfrom:
            if hasattr(obj, 'user_id')  and obj.user_id and obj.user_id.user_email:
                emailfrom = obj.user_id.user_email

        name = '[%d] %s' % (obj.id, tools.ustr(obj.name))
        emailfrom = tools.ustr(emailfrom)
        if hasattr(obj, 'section_id') and obj.section_id and obj.section_id.reply_to:
            reply_to = obj.section_id.reply_to
        else:
            reply_to = emailfrom
        if not emailfrom:
            raise osv.except_osv(_('Error!'), _("No E-Mail Found for your Company address!"))
        return mail_message.schedule_with_attach(cr, uid, emailfrom, emails, name, body, model='base.action.rule', reply_to=reply_to, res_id=str(obj.id))

    def do_check(self, cr, uid, action, obj, context=None):
        ok = super(base_action_rule, self).do_check(cr, uid, action, obj, context=context)

        if hasattr(obj, 'section_id'):
            ok = ok and (not action.trg_section_id or action.trg_section_id.id == obj.section_id.id)
        if hasattr(obj, 'categ_id'):
            ok = ok and (not action.trg_categ_id or action.trg_categ_id.id == obj.categ_id.id)

        #Cheking for history
        regex = action.regex_history
        if regex:
            res = False
            ptrn = re.compile(str(regex))
            for history in obj.message_ids:
                _result = ptrn.search(str(history.name))
                if _result:
                    res = True
                    break
            ok = ok and res

        if action.trg_max_history:
            res_count = False
            history_ids = filter(lambda x: x.email_from, obj.message_ids)
            if len(history_ids) <= action.trg_max_history:
                res_count = True
            ok = ok and res_count
        return ok

    def do_action(self, cr, uid, action, model_obj, obj, context=None):
        res = super(base_action_rule, self).do_action(cr, uid, action, model_obj, obj, context=context)
        write = {}

        if hasattr(action, 'act_section_id') and action.act_section_id:
            obj.section_id = action.act_section_id
            write['section_id'] = action.act_section_id.id

        if hasattr(obj, 'email_cc') and action.act_email_cc:
            if '@' in (obj.email_cc or ''):
                emails = obj.email_cc.split(",")
                if  obj.act_email_cc not in emails:# and '<'+str(action.act_email_cc)+">" not in emails:
                    write['email_cc'] = obj.email_cc + ',' + obj.act_email_cc
            else:
                write['email_cc'] = obj.act_email_cc

        # Put state change by rule in communication history
        if hasattr(obj, 'state') and action.act_state:
            model_obj.history(cr, uid, [obj], _(action.act_state))

        model_obj.write(cr, uid, [obj.id], write, context)
        emails = []

        if hasattr(obj, 'email_from') and action.act_mail_to_partner:
            emails.append(obj.email_from)
        emails = filter(None, emails)
        if len(emails) and action.act_mail_body:
            emails = list(set(emails))
            self.email_send(cr, uid, obj, emails, action.act_mail_body)
        return True


    def state_get(self, cr, uid, context=None):
        """Gets available states for crm"""
        res = super(base_action_rule, self).state_get(cr, uid, context=context)
        return res + crm.AVAILABLE_STATES

    def priority_get(self, cr, uid, context=None):
        res = super(base_action_rule, self).priority_get(cr, uid, context=context)
        return res + crm.AVAILABLE_PRIORITIES

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
