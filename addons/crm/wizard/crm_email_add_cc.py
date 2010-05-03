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

from osv import osv, fields
from tools.translate import _
import tools

class crm_email_add_cc_wizard(osv.osv_memory):
    """ Email Add CC"""

    _name = "crm.email.add.cc"
    _description = "Email Add CC"

    _columns = {
        'name': fields.selection([('user', 'User'), ('partner', 'Partner'), \
                         ('email', 'Email Address')], 'Send to', required=True), 
        'user_id': fields.many2one('res.users', "User"), 
        'partner_id': fields.many2one('res.partner', "Partner"), 
        'email': fields.char('Email', size=32), 
        'subject': fields.char('Subject', size=32), 
    }

    def on_change_email(self, cr, uid, ids, user, partner):

        """ @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of Mail’s IDs
        """

        if (not partner and not user):
            return {'value': {'email': False}}
        email = False
        if partner:
            addr = self.pool.get('res.partner').address_get(cr, uid, [partner], ['contact'])
            if addr and addr['contact']:
                email = self.pool.get('res.partner.address').read(cr, uid, addr['contact'] , ['email'])['email']
        elif user:
            addr = self.pool.get('res.users').read(cr, uid, user, ['address_id'])['address_id']
            if addr:
                email = self.pool.get('res.partner.address').read(cr, uid, addr[0] , ['email'])['email']
        return {'value': {'email': email}}


    def add_cc(self, cr, uid, ids, context={}):
        """
        Adds CC value in case 
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of create menu’s IDs
        @param context: A standard dictionary for contextual values
        """

        data = self.read(cr, uid, ids[0])
        email = data['email']
        subject = data['subject']

        if not context:
            return {}
        history_line = self.pool.get('crm.case.history').browse(cr, uid, context['active_id'])
        model = history_line.log_id.model_id.model
        model_pool = self.pool.get(model)
        case = model_pool.browse(cr, uid, history_line.log_id.res_id)
        body = history_line.description.replace('\n', '\n> ')
        if not case.email_from:
            raise osv.except_osv(_('Warning!'), ('No email Address defined for this case..'))
        if not email:
            raise osv.except_osv(_('Warning!'), ('Please Specify email address..'))
        flag = tools.email_send(
            case.user_id.address_id.email, 
            [case.email_from], 
            subject or '[' + str(case.id) + '] ' + case.name, 
            model_pool.format_body(body), 
            email_cc = [email], 
            openobject_id = str(case.id), 
            subtype = "html"
        )

        if flag:
            model_pool.write(cr, uid, case.id, {'email_cc' : case.email_cc and case.email_cc + ',' + email or email})
        else:
            raise osv.except_osv(_('Email Fail!'), ("Lastest Email is not sent successfully"))
        return {}

    def action_cancel(self, cr, uid, ids, context=None):
        return {'type' : 'ir.actions.act_window_close'}

crm_email_add_cc_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
