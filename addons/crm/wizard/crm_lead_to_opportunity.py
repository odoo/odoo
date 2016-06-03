# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class CrmLead2OpportunityPartner(models.TransientModel):
    _name = 'crm.lead2opportunity.partner'
    _description = 'Lead To Opportunity Partner'
    _inherit = 'crm.partner.binding'

    name = fields.Selection([
                ('convert', 'Convert to opportunity'),
                ('merge', 'Merge with existing opportunities')
            ], string='Conversion Action', required=True)
    opportunity_ids = fields.Many2many('crm.lead', string='Opportunities')
    user_id = fields.Many2one('res.users', string='Salesperson', index=True)
    team_id = fields.Many2one('crm.team', string='Sales Team', oldname='section_id', index=True)

    @api.onchange('action')
    def _onchange_action(self):
        self.partner_id = False if self.action != 'exist' else self._find_matching_partner()

    def _get_duplicated_leads(self, partner_id, email, include_lost=False):
        """
        Search for opportunities that have the same partner and that arent done or cancelled
        """
        return self.env['crm.lead']._get_duplicated_leads_by_emails(partner_id, email, include_lost=include_lost)

    @api.model
    def default_get(self, fields):
        """
        Default get for name, opportunity_ids.
        If there is an exisitng partner link to the lead, find all existing
        opportunities links with this partner to merge all information together
        """
        result = super(CrmLead2OpportunityPartner, self).default_get(fields)
        if self.env.context.get('active_id'):
            tomerge = [self.env.context['active_id']]
            partner_id = result.get('partner_id')
            lead_to_opp = self.env['crm.lead'].browse(tomerge)
            email = lead_to_opp.partner_id.email or lead_to_opp.email_from

            tomerge.extend(self._get_duplicated_leads(partner_id, email, include_lost=True))
            tomerge = list(set(tomerge))

            if 'action' in fields and not result.get('action'):
                result['action'] = partner_id and 'exist' or 'create'
            if 'partner_id' in fields:
                result['partner_id'] = partner_id
            if 'name' in fields:
                result['name'] = len(tomerge) >= 2 and 'merge' or 'convert'
            if 'opportunity_ids' in fields and len(tomerge) >= 2:
                result['opportunity_ids'] = tomerge
            if lead_to_opp.user_id:
                result['user_id'] = lead_to_opp.user_id.id
            if lead_to_opp.team_id:
                result['team_id'] = lead_to_opp.team_id.id
            if not partner_id and not lead_to_opp.contact_name:
                result['action'] = 'nothing'
        return result

    @api.onchange('user_id')
    def _onchange_user_id(self):
        """ When changing the user, also set a team_id or restrict team id
            to the ones user_id is member of. """
        user_id = self.user_id.id
        if user_id:
            team_id = self.team_id.id
            user_in_team = False
            if team_id:
                user_in_team = self.env['crm.team'].search_count([('id', '=', team_id), '|', ('user_id', '=', user_id), ('member_ids', '=', user_id)])
            if not user_in_team:
                result = self.env['crm.lead'].on_change_user(user_id)
                self.team_id = result['value'].get('team_id')

    @api.model
    def view_init(self, fields):
        """
        Check some preconditions before the wizard executes.
        """
        if self.env['crm.lead'].browse(self.env.context.get('active_ids')).filtered(lambda l: l.probability == 100):
            raise UserError(_("Closed/Dead leads cannot be converted into opportunities."))
        return False

    @api.multi
    def _convert_opportunity(self, vals):
        self.ensure_one()
        res = False
        lead_ids = vals.get('lead_ids', [])
        user_ids = vals.get('user_ids')
        team_id = vals.get('team_id')
        partner_id = vals.get('partner_id')
        leads_to_allocate = leads = self.env['crm.lead'].browse(lead_ids)
        for lead in leads:
            partner_id = self._create_partner(lead.id, self.action, partner_id or lead.partner_id.id)
            res = lead.convert_opportunity(partner_id, [], False)
        if self.env.context.get('no_force_assignation'):
            leads_to_allocate = leads.filtered(lambda l: not l.user_id)
        if user_ids:
            leads_to_allocate.allocate_salesman(user_ids, team_id=team_id)
        return res

    @api.multi
    def action_apply(self):
        """
        Convert lead to opportunity or merge lead and opportunity and open
        the freshly created opportunity view.
        """
        self.ensure_one()
        vals = {
            'team_id': self.team_id.id,
        }
        if self.partner_id:
            vals['partner_id'] = self.partner_id.id
        if self.name == 'merge':
            lead_id = self.opportunity_ids.merge_opportunity()
            lead = self.env['crm.lead'].browse(lead_id)
            if lead.type == "lead":
                vals.update({'lead_ids': lead.ids, 'user_ids': self.user_id.ids})
                self.with_context(active_ids=lead.ids)._convert_opportunity(vals)
            elif not self.env.context.get('no_force_assignation') or not lead.user_id:
                vals.update({'user_id': self.user_id.id})
                lead.write(vals)
        else:
            lead = self.env['crm.lead'].browse(self.env.context.get('active_ids'))
            vals.update({'lead_ids': lead.ids, 'user_ids': self.user_id.ids})
            self._convert_opportunity(vals)
            for lead in lead.filtered(lambda l: l.partner_id.user_id != l.user_id):
                lead.partner_id.write({'user_id': lead.user_id.id})

        return lead[0].redirect_opportunity_view()

    def _create_partner(self, lead_id, action, partner_id):
        """
        Create partner based on action.
        :return dict: dictionary organized as followed: {lead_id: partner_assigned_id}
        """
        #TODO this method in only called by crm_lead2opportunity_partner
        #wizard and would probably diserve to be refactored or at least
        #moved to a better place
        if action == 'each_exist_or_create':
            partner_id = self.with_context(active_id=lead_id)._find_matching_partner()
            action = 'create'
        res = self.env['crm.lead'].browse(lead_id).handle_partner_assignation(action, partner_id)
        return res.get(lead_id)

class CrmLead2OpportunityMassConvert(models.TransientModel):
    _name = 'crm.lead2opportunity.partner.mass'
    _description = 'Mass Lead To Opportunity Partner'
    _inherit = 'crm.lead2opportunity.partner'

    user_ids = fields.Many2many('res.users', string='Salesmen')
    team_id = fields.Many2one('crm.team', string='Sales Team', index=True, oldname='section_id')
    deduplicate = fields.Boolean(string='Apply deduplication', help='Merge with existing leads/opportunities of each partner', default=True)
    action = fields.Selection([
                ('each_exist_or_create', 'Use existing partner or create'),
                ('nothing', 'Do not link to a customer')
            ], 'Related Customer', required=True)
    force_assignation = fields.Boolean(string='Force assignation', help='If unchecked, this will leave the salesman of duplicated opportunities')

    @api.model
    def default_get(self, fields):
        res = super(CrmLead2OpportunityMassConvert, self).default_get(fields)
        if 'partner_id' in fields:
            # avoid forcing the partner of the first lead as default
            res['partner_id'] = False
        if 'action' in fields:
            res['action'] = 'each_exist_or_create'
        if 'name' in fields:
            res['name'] = 'convert'
        if 'opportunity_ids' in fields:
            res['opportunity_ids'] = False
        return res

    @api.onchange('action')
    def _onchange_action(self):
        if self.action != 'exist':
            self.partner_id = False

    @api.onchange('deduplicate')
    def _onchange_deduplicate(self):
        leads = self.env['crm.lead'].browse(self.env.context['active_ids'])
        partner_ids = [(lead.partner_id.id, lead.partner_id.email or lead.email_from) for lead in leads]
        partners_duplicated_leads = {}
        for partner_id, email in partner_ids:
            duplicated_lead_ids = self._get_duplicated_leads(partner_id, email)
            if len(duplicated_lead_ids) > 1:
                partners_duplicated_leads.setdefault((partner_id, email), []).extend(duplicated_lead_ids)
        leads_with_duplicates = []
        for lead in leads:
            lead_tuple = (lead.partner_id.id, lead.partner_id.email if lead.partner_id else lead.email_from)
            if len(partners_duplicated_leads.get(lead_tuple, [])) > 1:
                leads_with_duplicates.append(lead.id)
        self.opportunity_ids = leads_with_duplicates

    def _convert_opportunity(self, vals):
        """
        When "massively" (more than one at a time) converting leads to
        opportunities, check the salesteam_id and salesmen_ids and update
        the values before calling super.
        """
        self.ensure_one()
        vals.update({'user_ids': self.user_ids.ids, 'team_id': self.team_id.id})
        return super(CrmLead2OpportunityMassConvert, self)._convert_opportunity(vals)

    @api.multi
    def mass_convert(self):
        self.ensure_one()
        ctx = dict(self.env.context)
        Lead = self.env['crm.lead']
        if self.name == 'convert' and self.deduplicate:
            merged_lead_ids = []
            remaining_lead_ids = []
            lead_selected = ctx.get('active_ids')
            for lead_id in lead_selected:
                if lead_id not in merged_lead_ids:
                    lead = Lead.browse(lead_id)
                    duplicated_lead_rec = self._get_duplicated_leads(lead.partner_id.id, lead.partner_id.email or lead.email_from)
                    if len(duplicated_lead_rec) > 1:
                        duplicated_lead_rec = duplicated_lead_rec.sorted()
                        lead = duplicated_lead_rec.merge_opportunity()
                        merged_lead_ids.extend(duplicated_lead_rec.ids)
                        remaining_lead_ids.append(lead.id)
            active_ids = set(ctx.get('active_ids'))
            active_ids = active_ids.difference(merged_lead_ids)
            active_ids = active_ids.union(remaining_lead_ids)
            ctx['active_ids'] = list(active_ids)
        ctx['no_force_assignation'] = ctx.get('no_force_assignation', not self.force_assignation)
        return self.with_context(ctx).action_apply()
