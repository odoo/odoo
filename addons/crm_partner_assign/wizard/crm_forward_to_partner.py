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

import base64
import time
import re
from osv import osv, fields
import tools
from tools.translate import _

class crm_lead_forward_to_partner(osv.osv_memory):
    """Forwards lead history"""
    _name = 'crm.lead.forward.to.partner'
    _inherit = "crm.send.mail"

    _columns = {
        'name': fields.selection([('user', 'User'), ('partner', 'Partner'), \
                         ('email', 'Email Address')], 'Send to', required=True),
        'user_id': fields.many2one('res.users', "User"),
        'partner_id' : fields.many2one('res.partner', 'Partner'),
        'address_id' : fields.many2one('res.partner.address', 'Address'),
        'history': fields.selection([('info', 'Case Information'), ('latest', 'Latest email'), ('whole', 'Whole Story')], 'Send history', required=True),
    }

    _defaults = {
        'name' : 'email',
        'history': 'latest',
        'email_from': lambda self, cr, uid, *a: self.pool.get('res.users')._get_email_from(cr, uid, uid)[uid],
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
        email = self.pool.get('res.users')._get_email_from(cr, uid, [user])[user]
        return {'value': {'email_to': email}}

    def on_change_history(self, cr, uid, ids, history_type, context=None):
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
        res_id = context.get('active_id')
        msg_val = self._get_case_history(cr, uid, history_type, res_id, context=context)
        if msg_val:
            res = {'value': {'body' : '\n\n' + msg_val}}
        return res

    def _get_case_history(self, cr, uid, history_type, res_id, context=None):
        if not res_id:
            return

        msg_val = ''
        case_info = self.get_lead_details(cr, uid, res_id, context=context)
        model_pool = self.pool.get('crm.lead')

        if history_type == 'info':
            msg_val = case_info

        elif history_type == 'whole':
            log_ids = model_pool.browse(cr, uid, res_id, context=context).message_ids
            log_ids = map(lambda x: x.id, filter(lambda x: x.history, log_ids))
            msg_val = case_info + '\n\n' + self.get_whole_history(cr, uid, log_ids, context=context)

        elif history_type == 'latest':
            log_ids = model_pool.browse(cr, uid, res_id, context=context).message_ids
            log_ids = filter(lambda x: x.history and x.id, log_ids)
            if not log_ids:
                msg_val = case_info
            else:
                msg_val = case_info + '\n\n' + self.get_latest_history(cr, uid, log_ids[0].id, context=context)

        return msg_val

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

        partner_obj = self.pool.get('res.partner')
        addr = partner_obj.address_get(cr, uid, [partner_id], ['contact'])
        data = {'address_id': addr['contact']}
        data.update(self.on_change_address(cr, uid, ids, addr['contact'])['value'])

        partner = partner_obj.browse(cr, uid, [partner_id])
        user_id = partner and partner[0].user_id or False
        email = user_id and user_id.user_email or ''
        data.update({'email_cc' : email})
        return {
            'value' : data,
            'domain' : {'address_id' : partner_id and "[('partner_id', '=', partner_id)]" or "[]"}
            }

    def on_change_address(self, cr, uid, ids, address_id):
        email = ''
        if address_id:
            email = self.pool.get('res.partner.address').browse(cr, uid, address_id).email
        return {'value': {'email_to' : email}}

    def action_forward(self, cr, uid, ids, context=None):
        """
        Forward the lead to a partner
        """
        if context is None:
            context = {}
        this = self.browse(cr, uid, ids[0], context=context)
        case_pool = self.pool.get(context.get('active_model'))
        res_id = context and context.get('active_id', False) or False
        case = case_pool.browse(cr, uid, res_id, context=context)

        context.update({'mail': 'forward'})
        super(crm_lead_forward_to_partner, self).action_send(cr, uid, ids, context=context)

        to_write = {'date_assign': time.strftime('%Y-%m-%d')}
        if (this.name == 'partner' and this.partner_id):
            to_write['partner_assigned_id'] = this.partner_id.id

        if this.name == 'user':
            to_write.update({'user_id' : this.user_id.id})
        email_re = r'([^ ,<@]+@[^> ,]+)'
        email_cc = re.findall(email_re, case.email_cc or '')
        new_cc = []
        if case.email_cc:
            new_cc.append(case.email_cc)
        for to in this.email_to.split(','):
            email_to = re.findall(email_re, to)
            email_to = email_to and email_to[0] or ''
            if email_to not in email_cc:
                new_cc.append(to)
        to_write.update({'email_cc' : ', '.join(new_cc) })
        case_pool.write(cr, uid, case.id, to_write, context=context)

        return {'type': 'ir.actions.act_window_close'}

    def get_lead_details(self, cr, uid, lead_id, context=None):
        body = ["""Dear,

Below is possibly an interesting lead for you.

OpenERP Leads are now forwarded to our trusted partners, through our OpenERP CRM.
We hope that this one will provide you an interesting project, as they've recently contacted us showing interest in our software.

Please keep your account manager informed about the advancements of this lead or if you are not able to answer to its requests by replying to this email. This way, we can keep track of closed leads or forward them to other partners.

Please don't forget to propose our OpenERP Publisher's Warranty at the beginning of your implementation projects, together with your services quotation. The Warranty will provide unlimited bugfixing that will avoid you waste time on bugs detected during the implementation. It also provides free migration services for the current stable version at the time of signature; otherwise if we released a new version during your implementation, the customer would not always be able to easily migrate to newer versions. Please find all related information via http://www.openerp.com/services/pricing

Kind regards, OpenERP Team

            """, "\n\n"]
        lead_proxy = self.pool.get('crm.lead')
        lead = lead_proxy.browse(cr, uid, lead_id, context=context)
        if not lead.type or lead.type == 'lead' or not lead.partner_address_id:
                field_names = [
                    'partner_name', 'title', 'function', 'street', 'street2',
                    'zip', 'city', 'country_id', 'state_id', 'email_from',
                    'phone', 'fax', 'mobile', 'categ_id', 'description',
                ]

                for field_name in field_names:
                    field_definition = lead_proxy._columns[field_name]
                    value = None

                    if field_definition._type == 'selection':
                        if hasattr(field_definition.selection, '__call__'):
                            key = field_definition.selection(lead_proxy, cr, uid, context=context)
                        else:
                            key = field_definition.selection
                        value = dict(key).get(lead[field_name], lead[field_name])
                    elif field_definition._type == 'many2one':
                        if lead[field_name]:
                            value = lead[field_name].name_get()[0][1]
                    else:
                        value = lead[field_name]

                    body.append("%s: %s" % (field_definition.string, value or ''))
        elif lead.type == 'opportunity':
            pa = lead.partner_address_id
            body = [
                "Partner: %s" % (lead.partner_id and lead.partner_id.name_get()[0][1]),
                "Contact: %s" % (pa.name or ''),
                "Title: %s" % (pa.title or ''),
                "Function: %s" % (pa.function or ''),
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
                "Lead Category: %s" % (lead.categ_id and lead.categ_id.name or ''),
                "Details: %s" % (lead.description or ''),
            ]
        return "\n".join(body + ['---'])

    def default_get(self, cr, uid, fields, context=None):
        """
        This function gets default values
        """
        if context is None:
            context = {}

        defaults = super(crm_lead_forward_to_partner, self).default_get(cr, uid, fields, context=context)
        active_id = context.get('active_id')
        if not active_id:
            return defaults

        lead_proxy = self.pool.get('crm.lead')
        lead = lead_proxy.browse(cr, uid, active_id, context=context)

        body = self._get_case_history(cr, uid, defaults.get('history', 'latest'), lead.id, context=context)
        defaults.update({
            'subject' : '%s: %s' % (_('Fwd'), lead.name),
            'body' : body,
        })
        return defaults

crm_lead_forward_to_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
