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

from openerp.osv import fields, osv
from openerp.tools.translate import _

class crm_partner_binding(osv.osv_memory):
    """
    Handle the partner binding or generation in any CRM wizard that requires
    such feature, like the lead2opportunity wizard, or the
    phonecall2opportunity wizard.  Try to find a matching partner from the
    CRM model's information (name, email, phone number, etc) or create a new
    one on the fly.
    Use it like a mixin with the wizard of your choice.
    """
    _name = 'crm.partner.binding'
    _description = 'Handle partner binding or generation in CRM wizards.'
    _columns = {
        'action': fields.selection([
                ('exist', 'Link to an existing customer'),
                ('create', 'Create a new customer'),
                ('nothing', 'Do not link to a customer')
            ], 'Related Customer', required=True),
        'partner_id': fields.many2one('res.partner', 'Customer'),
    }

    def _find_matching_partner(self, cr, uid, context=None):
        """
        Try to find a matching partner regarding the active model data, like
        the customer's name, email, phone number, etc.

        :return int partner_id if any, False otherwise
        """
        if context is None:
            context = {}
        partner_id = False
        partner_obj = self.pool.get('res.partner')

        # The active model has to be a lead or a phonecall
        if (context.get('active_model') == 'crm.lead') and context.get('active_id'):
            active_model = self.pool.get('crm.lead').browse(cr, uid, context.get('active_id'), context=context)
        elif (context.get('active_model') == 'crm.phonecall') and context.get('active_id'):
            active_model = self.pool.get('crm.phonecall').browse(cr, uid, context.get('active_id'), context=context)

        # Find the best matching partner for the active model
        if (active_model):
            partner_obj = self.pool.get('res.partner')

            # A partner is set already
            if active_model.partner_id:
                partner_id = active_model.partner_id.id
            # Search through the existing partners based on the lead's email
            elif active_model.email_from:
                partner_ids = partner_obj.search(cr, uid, [('email', '=', active_model.email_from)], context=context)
                if partner_ids:
                    partner_id = partner_ids[0]
            # Search through the existing partners based on the lead's partner or contact name
            elif active_model.partner_name:
                partner_ids = partner_obj.search(cr, uid, [('name', 'ilike', '%'+active_model.partner_name+'%')], context=context)
                if partner_ids:
                    partner_id = partner_ids[0]
            elif active_model.contact_name:
                partner_ids = partner_obj.search(cr, uid, [
                        ('name', 'ilike', '%'+active_model.contact_name+'%')], context=context)
                if partner_ids:
                    partner_id = partner_ids[0]

        return partner_id

    def default_get(self, cr, uid, fields, context=None):
        res = super(crm_partner_binding, self).default_get(cr, uid, fields, context=context)
        partner_id = self._find_matching_partner(cr, uid, context=context)

        if 'action' in fields and not res.get('action'):
            res['action'] = partner_id and 'exist' or 'create'
        if 'partner_id' in fields:
            res['partner_id'] = partner_id

        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
