# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

import time
import re
from osv import osv, fields
from tools.translate import _
from mail.mail_message import to_email

class crm_lead_forward_to_partner(osv.osv_memory):
    """Forwards lead history"""
    _name = 'crm.lead.forward.to.partner'
    _inherit = "mail.compose.message"

    _columns = {
        'send_to': fields.selection([('user', 'User'), ('partner', 'Partner'), \
                         ('email', 'Email Address')], 'Send to', required=True),
        'user_id': fields.many2one('res.users', "User"),
        'attachment_ids': fields.many2many('ir.attachment','lead_forward_to_partner_attachment_rel', 'wizard_id', 'attachment_id', 'Attachments'),
        'partner_id' : fields.many2one('res.partner', 'Partner'),
        'history': fields.selection([('info', 'Case Information'), ('latest', 'Latest email'), ('whole', 'Whole Story')], 'Send history', required=True),
    }

    _defaults = {
        'send_to' : 'email',
        'history': 'latest',
        'email_from': lambda s, cr, uid, c: s.pool.get('res.users').browse(cr, uid, uid, c).email,
    }

    def on_change_email(self, cr, uid, ids, user, context=None):
        if not user:
            return {'value': {'email_to': False}}
        return {'value': {'email_to': self.pool.get('res.users').browse(cr, uid, uid, context=context).email}}

    def on_change_history(self, cr, uid, ids, history_type, context=None):
        """Gives message body according to type of history selected
            * info: Forward the case information
            * whole: Send the whole history
            * latest: Send the latest histoy
        """
        #TODO: ids and context are not comming
        res = {}
        res_id = context.get('active_id')
        model = context.get('active_model')
        lead = self.pool.get(model).browse(cr, uid, res_id, context)
        body = self._get_message_body(cr, uid, lead, history_type, context=context)
        if body:
            res = {'value': {'body' : body}}
        return res
    
    def on_change_partner(self, cr, uid, ids, partner_id):
        """This function fills address information based on partner/user selected
        """
        if not partner_id:
            return {'value' : {'email_to' : False}}
        partner_obj = self.pool.get('res.partner')
        data = {}
        partner = partner_obj.browse(cr, uid, [partner_id])
        user_id = partner and partner[0].user_id or False
        data.update({'email_from': partner and partner[0].email or "", 
                     'email_cc' : user_id and user_id.user or '', 
                     'user_id': user_id and user_id.id or False})
        return {'value' : data}

    def action_forward(self, cr, uid, ids, context=None):
        """
        Forward the lead to a partner
        """
        if context is None:
            context = {}
        res = {'type': 'ir.actions.act_window_close'}
        model = context.get('active_model')
        if model not in ('crm.lead'):
            return res

        this = self.browse(cr, uid, ids[0], context=context)
        lead = self.pool.get(model)
        lead_id = context and context.get('active_id', False) or False
        lead_ids = lead_id and [lead_id] or []
        mode = context.get('mail.compose.message.mode')
        if mode == 'mass_mail':
            lead_ids = context and context.get('active_ids', []) or []
            value = self.default_get(cr, uid, ['body', 'email_to', 'email_cc', 'subject', 'history'], context=context)
            self.write(cr, uid, ids, value, context=context)
            context['mail.compose.message.mode'] = mode

        self.send_mail(cr, uid, ids, context=context)
        for case in lead.browse(cr, uid, lead_ids, context=context):
            if (this.send_to == 'partner' and this.partner_id):
                lead.assign_partner(cr, uid, [case.id], this.partner_id.id, context=context)

            if this.send_to == 'user':
                lead.allocate_salesman(cr, uid, [case.id], [this.user_id.id], context=context)

            email_cc = to_email(case.email_cc)
            email_cc = email_cc and email_cc[0] or ''
            new_cc = []
            if email_cc:
                new_cc.append(email_cc)
            for to in this.email_to.split(','):
                email_to = to_email(to)
                email_to = email_to and email_to[0] or ''
                if email_to not in new_cc:
                    new_cc.append(to)
            update_vals = {'email_cc' : ', '.join(new_cc) }
            lead.write(cr, uid, [case.id], update_vals, context=context)
        return res

    def _get_info_body(self, cr, uid, lead, context=None):
        field_names = []
        proxy = self.pool.get(lead._name)
        if lead.type == 'opportunity':
            field_names += ['partner_id']
        field_names += [
           'partner_name' , 'title', 'function', 'street', 'street2',
            'zip', 'city', 'country_id', 'state_id', 'email_from',
            'phone', 'fax', 'mobile', 'categ_id', 'description',
        ]
        return proxy._mail_body(cr, uid, lead, field_names, context=context)

    def _get_message_body(self, cr, uid, lead, mode='whole', context=None):
        """This function gets whole communication history and returns as top posting style
        """
        mail_message = self.pool.get('mail.message')
        message_ids = []
        body = self._get_info_body(cr, uid, lead, context=context)
        if mode in ('whole', 'latest'):
            message_ids = lead.message_ids
            message_ids = map(lambda x: x.id, filter(lambda x: x.email_from, message_ids))
            if mode == 'latest' and len(message_ids):
                message_ids = [message_ids[0]]
            for message in mail_message.browse(cr, uid, message_ids, context=context):
                header = '-------- Original Message --------'
                sender = 'From: %s' %(message.email_from or '')
                to = 'To: %s' % (message.email_to or '')
                sentdate = 'Date: %s' % (message.date or '')
                desc = '\n%s'%(message.body)
                original = [header, sender, to, sentdate, desc, '\n']
                original = '\n'.join(original)
                body += original
        return body or ''

    def get_value(self, cr, uid, model, res_id, context=None):
        if context is None:
            context = {}
        res = super(crm_lead_forward_to_partner, self).get_value(cr, uid,  model, res_id, context=context)
        if model not in ("crm.lead"):
            return res
        proxy = self.pool.get(model)
        partner = self.pool.get('res.partner')
        lead = proxy.browse(cr, uid, res_id, context=context)
        mode = context.get('mail.compose.message.mode')
        if mode == "forward":
            body_type = context.get('mail.compose.message.body')
            email_cc = res.get('email_cc', "")
            email = res.get('email_to', "")
            subject = '%s: %s - %s' % (_('Fwd'), 'Lead forward', lead.name)
            body = self._get_message_body(cr, uid, lead, body_type, context=context)
            partner_assigned_id = lead.partner_assigned_id and lead.partner_assigned_id.id or False
            user_id = False
            if not partner_assigned_id:
                partner_assigned_id = proxy.search_geo_partner(cr, uid, [lead.id], context=None).get(lead.id, False)
            if partner_assigned_id:
                assigned_partner = partner.browse(cr, uid, partner_assigned_id, context=context)
                user_id = assigned_partner.user_id and assigned_partner.user_id.id or False
                email_cc = assigned_partner.user_id and assigned_partner.user_id.email or ''
                email = assigned_partner.email
            
            res.update({
                'subject' : subject,
                'body' : body,
                'email_cc' : email_cc,
                'email_to' : email,
                'partner_assigned_id': partner_assigned_id,
                'user_id': user_id,
            })
        return res
        

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        context['mail.compose.message.mode'] = 'forward'
        context['mail.compose.message.body'] = 'info'
        return super(crm_lead_forward_to_partner, self).default_get(cr, uid, fields, context=context)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
