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
        """
        if context is None:
            context = {}
        model = context.get('active_model')
        model = self.pool.get(model)
        rec_ids = context and context.get('active_ids', [])
        for this in model.browse(cr, uid, rec_ids, context=context):
            if this.partner_id:
                raise osv.except_osv(_('Warning !'),
                        _('A partner is already defined.'))

    def _select_partner(self, cr, uid, context=None):
        if context is None:
            context = {}
        lead = self.pool.get('crm.lead')
        partner = self.pool.get('res.partner')
        lead_ids = list(context and context.get('active_ids', []) or [])
        if not len(lead_ids):
            return False
        this = lead.browse(cr, uid, lead_ids[0], context=context)
        # Find partner address matches the email_from of the lead
        res = lead.message_partner_by_email(cr, uid, this.email_from, context=context)
        partner_id = res.get('partner_id', False)      
        # Find partner name that matches the name of the lead
        if not partner_id and this.partner_name:
            partner_ids = partner.search(cr, uid, [('name', '=', this.partner_name)], context=context)
            if partner_ids and len(partner_ids):
               partner_id = partner_ids[0]
        return partner_id

    def default_get(self, cr, uid, fields, context=None):
        """
        This function gets default values
        """
        res = super(crm_lead2partner, self).default_get(cr, uid, fields, context=context)        
        partner_id = self._select_partner(cr, uid, context=context)

        if 'partner_id' in fields:
            res.update({'partner_id': partner_id})
        if 'action' in fields:
            res.update({'action': partner_id and 'exist' or 'create'})
            
        return res

    def open_create_partner(self, cr, uid, ids, context=None):
        """
        This function Opens form of create partner.
        """
        view_obj = self.pool.get('ir.ui.view')
        view_id = view_obj.search(cr, uid, [('model', '=', self._name), \
                                     ('name', '=', self._name+'.view')])
        return {
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': view_id or False,
            'res_model': self._name,
            'context': context,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def _create_partner(self, cr, uid, ids, context=None):
        """
        This function Creates partner based on action.
        """
        if context is None:
            context = {}
        lead = self.pool.get('crm.lead')
        lead_ids = context and context.get('active_ids') or []
        data = self.browse(cr, uid, ids, context=context)[0]
        partner_id = data.partner_id and data.partner_id.id or False
        partner_ids = lead.convert_partner(cr, uid, lead_ids, data.action, partner_id, context=context)
        if context.get('mass_convert'):
            return partner_ids
        return partner_ids[lead_ids[0]]

    def make_partner(self, cr, uid, ids, context=None):
        """
        This function Makes partner based on action.
        """
        partner_id = self._create_partner(cr, uid, ids, context=context)
        return self.pool.get('res.partner').redirect_partner_form(cr, uid, partner_id, context=context)

crm_lead2partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
