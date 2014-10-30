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

from openerp import models, fields, api, _

class crm_partner_binding(models.TransientModel):
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

    action = fields.Selection([
            ('exist', 'Link to an existing customer'),
            ('create', 'Create a new customer'),
            ('nothing', 'Do not link to a customer')
        ], 'Related Customer', required=True)
    partner_id = fields.Many2one('res.partner', 'Customer')

    @api.multi
    def _find_matching_partner(self):
        """
        Try to find a matching partner regarding the active model data, like
        the customer's name, email, phone number, etc.

        :return int partner_id if any, False otherwise
        """
        partner_id = False
        partner_obj = self.env['res.partner']

        # The active model has to be a lead or a phonecall
        if (self._context.get('active_model') == 'crm.lead') and self._context.get('active_id'):
            active_model = self.pool['crm.lead'].browse(self._cr, self._uid, self._context.get('active_id'), context=self._context)
        elif (self._context.get('active_model') == 'crm.phonecall') and self._context.get('active_id'):
            active_model = self.env['crm.phonecall'].browse(self._context.get('active_id'))

        # Find the best matching partner for the active model
        if (active_model):
            # A partner is set already
            if active_model.partner_id:
                partner_id = active_model.partner_id.id
                
            # Search through the existing partners based on the lead's email
            elif active_model.email_from:
                partner_ids = partner_obj.search([('email', '=', active_model.email_from)])
                if partner_ids:
                    partner_id = partner_ids[0].id
            # Search through the existing partners based on the lead's partner or contact name
            elif active_model.partner_name:
                partner_ids = partner_obj.search([('name', 'ilike', '%'+active_model.partner_name+'%')])
                if partner_ids:
                    partner_id = partner_ids[0].id
            elif active_model.contact_name:
                partner_ids = partner_obj.search([('name', 'ilike', '%'+active_model.contact_name+'%')])
                if partner_ids:
                    partner_id = partner_ids[0].id
        return partner_id

    @api.model
    def default_get(self, fields):
        res = super(crm_partner_binding, self).default_get(fields)
        partner_id = self._find_matching_partner()
        if 'action' in fields:
            res['action'] = partner_id and 'exist' or 'create'
        if 'partner_id' in fields:
            res['partner_id'] = partner_id
        return res


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: