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
    _name = 'crm.lead.forward.to.partner'

    _columns = {
        'partner_id' : fields.many2one('res.partner', 'Partner'),
        'address_id' : fields.many2one('res.partner.address', 'Address'),
        'email_from' : fields.char('From', required=True, size=128),
        'email_to' : fields.char('To', required=True, size=128),
        'subject' : fields.char('Subject', required=True, size=128),
        'message' : fields.text('Message', required=True),
    }

    def on_change_partner(self, cr, uid, ids, partner_id):
        return {
            'domain' : {
                'address_id' : partner_id and "[('partner_id', '=', partner_id)]" or "[]",
            }
        }

    def on_change_address(self, cr, uid, ids, address_id):
        email = ''
        if address_id:
            email = self.pool.get('res.partner.address').browse(cr, uid, address_id).email

        return {
            'value' : {
                'email_to' : email,
            }
        }

    def action_cancel(self, cr, uid, ids, context=None):
        return {'type' : 'ir.actions.act_window_close'}

    def action_forward(self, cr, uid, ids, context=None):
        """
        Forward the lead to a partner
        """
        if context is None:
            context = {}

        res_id = context.get('active_id', False)

        if not res_id:
            return {}

        this = self.browse(cr, uid, ids[0], context=context)

        hist_obj = self.pool.get('crm.case.history')
        smtp_pool = self.pool.get('email.smtpclient')
        case_pool = self.pool.get('crm.lead')
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

        return {}

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

        field_names = [
            'partner_name', 'title', 'function_name', 'street', 'street2',
            'zip', 'city', 'country_id', 'state_id', 'email_from',
            'phone', 'fax', 'mobile'
        ]

        message = []

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

        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        email_from = ''
        if user.address_id and user.address_id.email:
            email_from = "%s <%s>" % (user.name, user.address_id.email)

        res = {
            'email_from' : email_from,
            'subject' : '[Lead-Forward:%06d] %s' % (lead.id, lead.name),
            'message' : "\n".join(message + ['---']),
        }

        return res

crm_lead_forward_to_partner()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
