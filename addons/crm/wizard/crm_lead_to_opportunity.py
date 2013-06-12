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
from openerp import tools
import re

class crm_lead2opportunity_partner(osv.osv_memory):
    _name = 'crm.lead2opportunity.partner'
    _description = 'Lead To Opportunity Partner'
    _inherit = 'crm.partner.binding'

    _columns = {
        'name': fields.selection([
                ('convert', 'Convert to opportunity'),
                ('merge', 'Merge with existing opportunities')
            ], 'Conversion Action', required=True),
        'opportunity_ids': fields.many2many('crm.lead', string='Opportunities'),
    }

    def default_get(self, cr, uid, fields, context=None):
        """
        Default get for name, opportunity_ids.
        If there is an exisitng partner link to the lead, find all existing
        opportunities links with this partner to merge all information together
        """
        lead_obj = self.pool.get('crm.lead')

        res = super(crm_lead2opportunity_partner, self).default_get(cr, uid, fields, context=context)
        if context.get('active_id'):
            tomerge = set([int(context['active_id'])])

            email = False
            partner_id = res.get('partner_id')
            lead = lead_obj.browse(cr, uid, int(context['active_id']), context=context)

            #TOFIX: use mail.mail_message.to_mail
            email = re.findall(r'([^ ,<@]+@[^> ,]+)', lead.email_from or '')

            if partner_id:
                # Search for opportunities that have the same partner and that arent done or cancelled
                ids = lead_obj.search(cr, uid, [('partner_id', '=', partner_id), ('state', '!=', 'done')])
                for id in ids:
                    tomerge.add(id)
            if email:
                ids = lead_obj.search(cr, uid, [('email_from', 'ilike', email[0]), ('state', '!=', 'done')])
                for id in ids:
                    tomerge.add(id)

            if 'action' in fields:
                res.update({'action' : partner_id and 'exist' or 'create'})
            if 'partner_id' in fields:
                res.update({'partner_id' : partner_id})
            if 'name' in fields:
                res.update({'name' : len(tomerge) >= 2 and 'merge' or 'convert'})
            if 'opportunity_ids' in fields and len(tomerge) >= 2:
                res.update({'opportunity_ids': list(tomerge)})

        return res

    def view_init(self, cr, uid, fields, context=None):
        """
        Check some preconditions before the wizard executes.
        """
        if context is None:
            context = {}
        lead_obj = self.pool.get('crm.lead')
        for lead in lead_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            if lead.state in ['done', 'cancel']:
                raise osv.except_osv(_("Warning!"), _("Closed/Cancelled leads cannot be converted into opportunities."))
        return False

    def _convert_opportunity(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        lead = self.pool.get('crm.lead')
        res = False
        partner_ids_map = self._create_partner(cr, uid, ids, context=context)
        lead_ids = vals.get('lead_ids', [])
        team_id = vals.get('section_id', False)
        for lead_id in lead_ids:
            partner_id = partner_ids_map.get(lead_id, False)
            # FIXME: cannot pass user_ids as the salesman allocation only works in batch
            res = lead.convert_opportunity(cr, uid, [lead_id], partner_id, [], team_id, context=context)
        # FIXME: must perform salesman allocation in batch separately here
        user_ids = vals.get('user_ids', False)
        if user_ids:
            lead.allocate_salesman(cr, uid, lead_ids, user_ids, team_id=team_id, context=context)
        return res

    def action_apply(self, cr, uid, ids, context=None):
        """
        Convert lead to opportunity or merge lead and opportunity and open
        the freshly created opportunity view.
        """
        if context is None:
            context = {}

        w = self.browse(cr, uid, ids, context=context)[0]
        opp_ids = [o.id for o in w.opportunity_ids]
        if w.name == 'merge':
            lead_id = self.pool.get('crm.lead').merge_opportunity(cr, uid, opp_ids, context=context)
            lead_ids = [lead_id]
            lead = self.pool.get('crm.lead').read(cr, uid, lead_id, ['type'], context=context)
            if lead['type'] == "lead":
                context.update({'active_ids': lead_ids})
                self._convert_opportunity(cr, uid, ids, {'lead_ids': lead_ids}, context=context)
        else:
            lead_ids = context.get('active_ids', [])
            self._convert_opportunity(cr, uid, ids, {'lead_ids': lead_ids}, context=context)

        return self.pool.get('crm.lead').redirect_opportunity_view(cr, uid, lead_ids[0], context=context)

    def _create_partner(self, cr, uid, ids, context=None):
        """
        Create partner based on action.
        :return dict: dictionary organized as followed: {lead_id: partner_assigned_id}
        """
        #TODO this method in only called by crm_lead2opportunity_partner
        #wizard and would probably diserve to be refactored or at least
        #moved to a better place
        if context is None:
            context = {}
        lead = self.pool.get('crm.lead')
        lead_ids = context.get('active_ids', [])
        data = self.browse(cr, uid, ids, context=context)[0]
        partner_id = data.partner_id and data.partner_id.id or False
        return lead.handle_partner_assignation(cr, uid, lead_ids, data.action, partner_id, context=context)

class crm_lead2opportunity_mass_convert(osv.osv_memory):
    _name = 'crm.lead2opportunity.partner.mass'
    _description = 'Mass Lead To Opportunity Partner'
    _inherit = 'crm.lead2opportunity.partner'

    _columns = {
        'user_ids':  fields.many2many('res.users', string='Salesmen'),
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
    }

    def default_get(self, cr, uid, fields, context=None):
        res = super(crm_lead2opportunity_mass_convert, self).default_get(cr, uid, fields, context)
        if 'partner_id' in fields:
            # avoid forcing the partner of the first lead as default
            res['partner_id'] = False
        if 'action' in fields:
            res['action'] = 'create'
        if 'name' in fields:
            res['name'] = 'convert'
        if 'opportunity_ids' in fields:
            res['opportunity_ids'] = False
        return res

    def _convert_opportunity(self, cr, uid, ids, vals, context=None):
        """
        When "massively" (more than one at a time) converting leads to
        opportunities, check the salesteam_id and salesmen_ids and update
        the values before calling super.
        """
        if context is None:
            context = {}
        data = self.browse(cr, uid, ids, context=context)[0]
        salesteam_id = data.section_id and data.section_id.id or False
        salesmen_ids = []
        if data.user_ids:
            salesmen_ids = [x.id for x in data.user_ids]
        vals.update({'user_ids': salesmen_ids, 'section_id': salesteam_id})
        return super(crm_lead2opportunity_mass_convert, self)._convert_opportunity(cr, uid, ids, vals, context=context)

    def mass_convert(self, cr, uid, ids, context=None):
        return self.action_apply(cr, uid, ids, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
