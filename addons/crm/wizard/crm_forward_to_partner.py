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
import tools

class crm_lead_forward_to_partner(osv.osv_memory):
    """Forwards lead history"""
    _name = 'crm.lead.forward.to.partner'

    _columns = {
        'name': fields.selection([('user', 'User'), ('partner', 'Partner'), \
                         ('email', 'Email Address')], 'Send to', required=True), 
        'user_id': fields.many2one('res.users', "User"), 
        'partner_id' : fields.many2one('res.partner', 'Partner'), 
        'address_id' : fields.many2one('res.partner.address', 'Address'), 
        'email_from' : fields.char('From', required=True, size=128), 
        'email_to' : fields.char('To', required=True, size=128), 
        'subject' : fields.char('Subject', required=True, size=128), 
        'message' : fields.text('Message', required=True), 
        'history': fields.selection([('latest', 'Latest email'), ('whole', 'Whole Story'), ('info', 'Case Information')], 'Send history', required=True),
        'add_cc': fields.boolean('Add as CC', required=False, help="Selcect if you want this user to add as cc for this case.This user will receive all future conversations"),  
    }
    
    def get_whole_history(self, cr, uid, ids, context=None):
        """This function gets whole communication history and returns as top posting style 
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of history IDs
        @param context: A standard dictionary for contextual values
        """
        whole = []
        for hist_id in ids:
            whole.append(self.get_latest_history(cr, uid, hist_id, context=context))
        whole = '\n\n'.join(whole)
        return whole or ''

    def get_latest_history(self, cr, uid, hist_id, context=None):
        """This function gets latest communication and returns as top posting style
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param hist_id: Id of latest history
        @param context: A standard dictionary for contextual values
        """
        log_pool = self.pool.get('mailgate.message')
        hist = log_pool.browse(cr, uid, hist_id, context=context)
        header = '-------- Original Message --------'
        sender = 'From: %s' %(hist.email_from or '')
        to = 'To: %s' % (hist.email_to or '')
        sentdate = 'Date: %s' % (hist.date or '')
        desc = '\n%s'%(hist.description)
        original = [header, sender, to, sentdate, desc]
        original = '\n'.join(original)
        return original

    def on_change_email(self, cr, uid, ids, user):
        """This function fills email information based on user selected
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Mail’s IDs
        @param user: Changed User id
        @param partner: Changed Partner id  
        """
        if not user:
            return {'value': {'email_to': False}}
        email = False
        addr = self.pool.get('res.users').read(cr, uid, user, ['address_id'])['address_id']
        if addr:
            email = self.pool.get('res.partner.address').read(cr, uid, addr[0] , ['email'])['email']
        return {'value': {'email_to': email}}

    def on_change_history(self, cr, uid, ids, history, context=None):
        """Gives message body according to type of history selected
            * info: Forward the case information
            * whole: Send the whole history
            * latest: Send the latest histoy
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of history IDs
        @param context: A standard dictionary for contextual values
        """
        #TODO: ids and context are not comming
        res = False
        msg_val = ''
        res_id = False # Comes from context
        model = None # Comes from context
        model_pool = self.pool.get(model)
        if not res_id or not model:
            return res
        if history == 'info':
            msg_val = self.get_lead_details(cr, uid, res_id, context=context)

        if history == 'whole':
            log_ids = model_pool.browse(cr, uid, res_id, context=context).message_ids
            log_ids = map(lambda x: x.id, log_ids)
            if not log_ids:
                raise osv.except_osv('Warning!', 'There is no history to send')
            msg_val = self.get_whole_history(cr, uid, log_ids, context=context)

        if history == 'latest':
            log_ids = model_pool.browse(cr, uid, res_id, context=context).message_ids
            if not log_ids:
                raise osv.except_osv('Warning!', 'There is no history to send')
            msg_val = self.get_latest_history(cr, uid, log_ids[0].id, context=context)

        if msg_val:
            res = {'value': {'message' : '\n\n' + msg_val}}
        return res

    def on_change_partner(self, cr, uid, ids, partner_id):
        """This function fills address information based on partner/user selected
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Mail’s IDs
        @param user: Changed User id
        @param partner: Changed Partner id  
        """
        if not partner_id:
            return {'value' : {'email_to' : False, 'address_id': False}}

        addr = self.pool.get('res.partner').address_get(cr, uid, [partner_id], ['contact'])
        data = {'address_id': addr['contact']}
        data.update(self.on_change_address(cr, uid, ids, addr['contact'])['value'])
        return {
            'value' : data, 
            'domain' : {'address_id' : partner_id and "[('partner_id', '=', partner_id)]" or "[]"}
            }

    def on_change_address(self, cr, uid, ids, address_id):
        email = ''
        if address_id:
            email = self.pool.get('res.partner.address').browse(cr, uid, address_id).email
        return {'value': {'email_to' : email}}

    def action_cancel(self, cr, uid, ids, context=None):
        return {'type' : 'ir.actions.act_window_close'}

    def action_forward(self, cr, uid, ids, context=None):
        """
        Forward the lead to a partner
        """
        if context is None:
            context = {}

        res_id = context.get('active_id', False)
        
        model = context.get('active_model', False)
        if not res_id or not model:
            return {}

        this = self.browse(cr, uid, ids[0], context=context)

        hist_obj = self.pool.get('crm.case.history')
        smtp_pool = self.pool.get('email.smtpclient')
        case_pool = self.pool.get(model)
        case = case_pool.browse(cr, uid, res_id, context=context)

        emails = [this.email_to]
        body = case_pool.format_body(this.message)
        email_from = this.email_from or False
        case_pool._history(cr, uid, [case], _('Forward'), history=True, email=this.email_to, details=body, email_from=email_from)

        flag = False
        if case.section_id and case.section_id.server_id:
            flag = smtp_pool.send_email(
                cr=cr, 
                uid=uid, 
                server_id=case.section_id.server_id.id, 
                emailto=emails, 
                subject=this.subject, 
                body="<pre>%s</pre>" % body, 
            )
        else:
            flag = tools.email_send(
                email_from, 
                emails, 
                this.subject, 
                body, 
            )
        if this.add_cc:
            case_pool.write(cr, uid, case.id, {'email_cc' : case.email_cc and case.email_cc + ', ' + this.email_to or this.email_to})
        return {}

    def get_lead_details(self, cr, uid, lead_id, context=None):
        message = []
        lead_proxy = self.pool.get('crm.lead')
        lead = lead_proxy.browse(cr, uid, lead_id, context=context)
        if lead.type == 'lead':
                field_names = [
                    'partner_name', 'title', 'function_name', 'street', 'street2', 
                    'zip', 'city', 'country_id', 'state_id', 'email_from', 
                    'phone', 'fax', 'mobile'
                ]
        
                for field_name in field_names:
                    field_definition = lead_proxy._columns[field_name]
                    value = None
        
                    if field_definition._type == 'selection':
                        if hasattr(field_definition.selection, '__call__'):
                            key = field_definition.selection(lead_proxy, cr, uid, context=context)
                        else:
                            key = field.definition.selection
                        value = dict(key).get(lead[field_name], lead[field_name])
                    elif field_definition._type == 'many2one':
                        if lead[field_name]:
                            value = lead[field_name].name_get()[0][1]
                    else:
                        value = lead[field_name]
        
                    message.append("%s: %s" % (field_definition.string, value or ''))
        elif lead.type == 'opportunity':
            pa = lead.partner_address_id
            message = [
            "Partner: %s" % (lead.partner_id.name_get()[0][1]), 
            "Contact: %s" % (pa.name or ''), 
            "Title: %s" % (pa.title or ''), 
            "Function: %s" % (pa.function and pa.function.name_get()[0][1] or ''), 
            "Street: %s" % (pa.street or ''), 
            "Street2: %s" % (pa.street2 or ''), 
            "Zip: %s" % (pa.zip or ''), 
            "City: %s" % (pa.city or ''), 
            "Country: %s" % (pa.country_id and pa.country_id.name_get()[0][1] or ''), 
            "State: %s" % (pa.state_id and pa.state_id.name_get()[0][1] or ''), 
            "Email: %s" % (pa.email or ''), 
            "Phone: %s" % (pa.phone or ''), 
            "Fax: %s" % (pa.fax or ''), 
            "Mobile: %s" % (pa.mobile or ''), 
            ]
        return "\n".join(message + ['---'])
        
    def default_get(self, cr, uid, fields, context=None):
        """
        This function gets default values
        """
        if context is None:
            context = {}

        active_ids = context.get('active_ids')
        if not active_ids:
            return {}

        lead_proxy = self.pool.get('crm.lead')
        lead = lead_proxy.browse(cr, uid, active_ids[0], context=context)
        message = False
        
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        email_from = ''
        if user.address_id and user.address_id.email:
            email_from = "%s <%s>" % (user.name, user.address_id.email)
        
        message = self.get_lead_details(cr, uid, lead.id, context=context)

        res = {
            'email_from' : email_from, 
            'subject' : '[%s-Forward:%06d] %s' % (lead.type.title(), lead.id, lead.name), 
            'message' : message, 
        }
        if 'history' in fields:
            res.update({'history': 'info'})
        return res

crm_lead_forward_to_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
