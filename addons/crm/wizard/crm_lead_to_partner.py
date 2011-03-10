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
import re

class crm_lead2partner(osv.osv_memory):
    """ Converts lead to partner """

    _name = 'crm.lead2partner'
    _description = 'Lead to Partner'

    _columns = {
        'action': fields.selection([('exist', 'Link to an existing partner'), \
                                    ('create', 'Create a new partner')], \
                                    'Action', required=True),
        'partner_id': fields.many2one('res.partner', 'Partner'),
    }

    def view_init(self, cr, uid, fields, context=None):
        """
        This function checks for precondition before wizard executes
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param fields: List of fields for default value
        @param context: A standard dictionary for contextual values

        """

        lead_obj = self.pool.get('crm.lead')
        rec_ids = context and context.get('active_ids', [])
        for lead in lead_obj.browse(cr, uid, rec_ids, context=context):
            if lead.partner_id:
                     raise osv.except_osv(_('Warning !'),
                        _('A partner is already defined on this lead.'))

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

        lead_obj = self.pool.get('crm.lead')
        partner_obj = self.pool.get('res.partner')
        contact_obj = self.pool.get('res.partner.address')
        partner_id = False

        data = context and context.get('active_ids', []) or []
        res = super(crm_lead2partner, self).default_get(cr, uid, fields, context=context)

        for lead in lead_obj.browse(cr, uid, data, context=context):
            partner_ids = []
            # Find partner address matches the email_from of the lead
            email = re.findall(r'([^ ,<@]+@[^> ,]+)', lead.email_from or '')
            email = map(lambda x: "'" + x + "'", email)
            if email:
                cr.execute("""select id from res_partner_address
                                where
                                substring(email from '([^ ,<@]+@[^> ,]+)') in (%s)""" % (','.join(email)))
                address_ids = map(lambda x: x[0], cr.fetchall())
                if address_ids:
                    addresses = contact_obj.browse(cr, uid, address_ids)
                    partner_ids = addresses and [addresses[0].partner_id.id] or False

            # Find partner name that matches the name of the lead
            if not partner_ids and lead.partner_name:
                partner_ids = partner_obj.search(cr, uid, [('name', '=', lead.partner_name)], context=context)
            if not partner_ids:
                cr.execute("""SELECT p.id from res_partner p
                            where regexp_replace(lower(p.name), '[^a-z]*', '', 'g') = regexp_replace(%s, '[^a-z]*', '', 'g')""", (lead.name.lower(), ))
                partner_ids = map(lambda x: x[0], cr.fetchall())
            partner_id = partner_ids and partner_ids[0] or False

            if 'partner_id' in fields:
                res.update({'partner_id': partner_id})
            if 'action' in fields:
                res.update({'action': partner_id and 'exist' or 'create'})
            if 'opportunity_ids' in fields:
                res.update({'opportunity_ids': data})

        return res

    def open_create_partner(self, cr, uid, ids, context=None):
        """
        This function Opens form of create partner.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Lead to Partner's IDs
        @param context: A standard dictionary for contextual values

        @return : Dictionary value for next form.
        """
        if context is None:
            context = {}

        view_obj = self.pool.get('ir.ui.view')
        view_id = view_obj.search(cr, uid, [('model', '=', 'crm.lead2partner'), \
                                     ('name', '=', 'crm.lead2partner.view')])
        return {
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': view_id or False,
            'res_model': 'crm.lead2partner',
            'context': context,
            'type': 'ir.actions.act_window',
            'target': 'new',
            }


    def _create_partner(self, cr, uid, ids, context=None):
        """
        This function Creates partner based on action.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Lead to Partner's IDs
        @param context: A standard dictionary for contextual values

        @return : Dictionary {}.
        """
        if context is None:
            context = {}

        lead_obj = self.pool.get('crm.lead')
        partner_obj = self.pool.get('res.partner')
        contact_obj = self.pool.get('res.partner.address')
        partner_ids = []
        partner_id = False
        contact_id = False
        rec_ids = context and context.get('active_ids', [])

        for data in self.browse(cr, uid, ids, context=context):
            for lead in lead_obj.browse(cr, uid, rec_ids, context=context):
                if data.action == 'create':
                    partner_id = partner_obj.create(cr, uid, {
                        'name': lead.partner_name or lead.contact_name or lead.name,
                        'user_id': lead.user_id.id,
                        'comment': lead.description,
                    })
                    contact_id = contact_obj.create(cr, uid, {
                        'partner_id': partner_id,
                        'name': lead.contact_name,
                        'phone': lead.phone,
                        'mobile': lead.mobile,
                        'email': lead.email_from,
                        'fax': lead.fax,
                        'title': lead.title and lead.title.id or False,
                        'function': lead.function,
                        'street': lead.street,
                        'street2': lead.street2,
                        'zip': lead.zip,
                        'city': lead.city,
                        'country_id': lead.country_id and lead.country_id.id or False,
                        'state_id': lead.state_id and lead.state_id.id or False,
                    })

                else:
                    if data.partner_id:
                        partner_id = data.partner_id.id
                        contact_id = partner_obj.address_get(cr, uid, [partner_id])['default']
                self.assign_partner(cr, uid, lead.id, partner_id)
                partner_ids.append(partner_id)
        return partner_ids


    def assign_partner(self, cr, uid, lead_id, partner_id):
        self.pool.get("crm.lead").write(cr, uid, [lead_id], {'partner_id' : partner_id})


    def make_partner(self, cr, uid, ids, context=None):
        """
        This function Makes partner based on action.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Lead to Partner's IDs
        @param context: A standard dictionary for contextual values

        @return : Dictionary value for created Partner form.
        """
        if context is None:
            context = {}

        partner_ids = self._create_partner(cr, uid, ids, context=context)
        mod_obj = self.pool.get('ir.model.data')
        result = mod_obj._get_id(cr, uid, 'base', 'view_res_partner_filter')
        res = mod_obj.read(cr, uid, result, ['res_id'])
        return {'type': 'ir.actions.act_window_close'}

crm_lead2partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
