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
import re

class crm_lead2opportunity_partner(osv.osv_memory):
    _name = 'crm.lead2opportunity.partner'
    _description = 'Lead To Opportunity Partner'
    _inherit = 'crm.lead2partner'

    _columns = {
        'action': fields.selection([('exist', 'Link to an existing partner'), \
                                    ('create', 'Create a new partner'), \
                                    ('nothing', 'Do not link to a partner')], \
                                    'Related Partner', required=True),
        'name': fields.selection([('convert', 'Convert to Opportunities'), ('merge', 'Merge with existing Opportunities')], 'Conversion Action', required=True),
        'opportunity_ids': fields.many2many('crm.lead', string='Opportunities', domain=[('type', '=', 'opportunity')]),
    }

    def default_get(self, cr, uid, fields, context=None):
        """
            Default get for name, opportunity_ids
            if there is an exisitng  partner link to the lead, find all existing opportunity link with this partnet to merge
            all information together
        """
        lead_obj = self.pool.get('crm.lead')

        res = super(crm_lead2opportunity_partner, self).default_get(cr, uid, fields, context=context)
        opportunities = res.get('opportunity_ids') or []
        partner_id = False
        email = False
        for lead in lead_obj.browse(cr, uid, opportunities, context=context):
            partner_id = lead.partner_id and lead.partner_id.id or False

            #TOFIX: use mail.mail_message.to_mail
            email = re.findall(r'([^ ,<@]+@[^> ,]+)', lead.email_from or '')
            email = map(lambda x: "'" + x + "'", email)

        if not partner_id and res.get('partner_id'):
            partner_id = res.get('partner_id')

        ids = []
        if partner_id:
            ids = lead_obj.search(cr, uid, [('partner_id', '=', partner_id), ('type', '=', 'opportunity'), '!', ('state', 'in', ['done', 'cancel'])])
            if ids:
                opportunities.append(ids[0])
        if not partner_id:
            if email:
                # Find email of existing opportunity matches the email_from of the lead
                cr.execute("""select id from crm_lead where type='opportunity' and
                                substring(email_from from '([^ ,<@]+@[^> ,]+)') in (%s)""" % (','.join(email)))
                ids = map(lambda x:x[0], cr.fetchall())
            if ids:
                opportunities.append(ids[0])

        if 'action' in fields:
            res.update({'action' : partner_id and 'exist' or 'create'})
        if 'partner_id' in fields:
            res.update({'partner_id' : partner_id})
        if 'name' in fields:
            res.update({'name' : ids and 'merge' or 'convert'})
        if 'opportunity_ids' in fields:
            res.update({'opportunity_ids': opportunities})


        return res

    def view_init(self, cr, uid, fields, context=None):
        """
        This function checks for precondition before wizard executes
        """
        if context is None:
            context = {}
        lead_obj = self.pool.get('crm.lead')
        for lead in lead_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            if lead.state in ['done', 'cancel']:
                raise osv.except_osv(_("Warning !"), _("Closed/Cancelled leads cannot be converted into opportunities."))
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

    def _merge_opportunity(self, cr, uid, ids, opportunity_ids, action='merge', context=None):
        if context is None:
            context = {}
        res = False
        # Expected: all newly-converted leads (active_ids) will be merged with the opportunity(ies)
        # that have been selected in the 'opportunity_ids' m2m, with all these records
        # merged into the first opportunity (and the rest deleted)
        opportunity_ids = [o.id for o in opportunity_ids]
        lead_ids = context.get('active_ids', [])
        if action == 'merge' and lead_ids and opportunity_ids:
            # Add the leads in the to-merge list, next to other opps
            # (the fact that they're passed in context['lead_ids'] means that
            # they cannot be selected to contain the result of the merge.
            opportunity_ids.extend(lead_ids)
            context.update({'lead_ids': lead_ids, "convert" : True})
            res = self.pool.get('crm.lead').merge_opportunity(cr, uid, opportunity_ids, context=context)
        return res

    def action_apply(self, cr, uid, ids, context=None):
        """
        This converts lead to opportunity and opens Opportunity view
        """
        if not context:
            context = {}
        lead = self.pool.get('crm.lead')
        lead_ids = context.get('active_ids', [])
        data = self.browse(cr, uid, ids, context=context)[0]
        self._convert_opportunity(cr, uid, ids, {'lead_ids': lead_ids}, context=context)
        self._merge_opportunity(cr, uid, ids, data.opportunity_ids, data.name, context=context)
        return lead.redirect_opportunity_view(cr, uid, lead_ids[0], context=context)


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
        data = self.browse(cr, uid, ids, context=context)[0]
        salesteam_id = data.section_id and data.section_id.id or False
        salesman = []
        if data.user_ids:
            salesman = [x.id for x in data.user_ids]
        vals.update({'user_ids': salesman, 'section_id': salesteam_id})
        return super(crm_lead2opportunity_mass_convert, self)._convert_opportunity(cr, uid, ids, vals, context=context)

    def mass_convert(self, cr, uid, ids, context=None):
        return self.action_apply(cr, uid, ids, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
