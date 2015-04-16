# -*- coding: utf-8 -*-

import re

from openerp import api, fields, models, _
from openerp.exceptions import UserError


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
    team_id = fields.Many2one(
        'crm.team', string='Sales Team', oldname='section_id', index=True)

    @api.model
    def view_init(self, fields):
        """
        Check some preconditions before the wizard executes.
        """
        for lead in self.env['crm.lead'].browse(self.env.context.get('active_ids', [])):
            if lead.probability == 100:
                raise UserError(_("Closed/Dead leads cannot be converted into opportunities."))
        return False

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
            tomerge = [int(self.env.context['active_id'])]
            partner_id = result.get('partner_id')
            lead_to_opp = self.env['crm.lead'].browse(int(self.env.context['active_id']))
            email = lead_to_opp.partner_id.email or lead_to_opp.email_from
            duplicate_lead = self._get_duplicated_leads(
                partner_id, email, include_lost=True)
            tomerge.extend(duplicate_lead.ids)
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

    @api.onchange('action')
    def onchange_action(self):
        self.partner_id = False if self.action != 'exist' else self._find_matching_partner()

    @api.onchange('user_id')
    def on_change_user(self):
        """ When changing the user, also set a team_id or restrict team id
            to the ones user_id is member of. """
        team_id = self.team_id.id
        if self.user_id:
            if self.team_id:
                user_in_team = self.env['crm.team'].search(
                    [('id', '=', self.team_id.id), '|', ('user_id', '=', self.user_id.id), ('member_ids', '=', self.user_id.id)], count=True)
            else:
                user_in_team = False
            if not user_in_team:
                lead_to_opp = self.env['crm.lead'].browse(
                    self.env.context.get('active_id'))
                lead_to_opp.user_id = self.user_id
                lead_to_opp.on_change_user()
                team_id = lead_to_opp.team_id
        self.team_id = team_id

    def _convert_opportunity(self, vals):
        res = False
        leads = vals.get('lead_ids', [])
        team_id = vals.get('team_id', False)
        partner_id = vals.get('partner_id', False)
        for lead in leads:
            partner_id = self._create_partner(lead, self.action, partner_id or lead.partner_id)
            res = lead.convert_opportunity(partner_id, [], False)
        user_ids = vals.get('user_ids')

        if self.env.context.get('no_force_assignation'):
            leads_to_allocate = leads.filtered(lambda l: not l.user_id)
        else:
            leads_to_allocate = leads
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
        context =  self.env.context
        vals = {
            'team_id': self.team_id.id,
        }
        if self.partner_id:
            vals['partner_id'] = self.partner_id
        if self.name == 'merge':
            lead = self.opportunity_ids.merge_opportunity()
            if lead.type == "lead":
                vals.update({'lead_ids': lead, 'user_ids': [self.user_id.id]})
                self.with_context(active_ids=[lead.id])._convert_opportunity(vals)
            elif not context.get('no_force_assignation') or not lead.user_id:
                vals.update({'user_id': self.user_id.id, 'partner_id': self.partner_id.id})
                lead.write(vals)
        else:
            lead_ids = self.env.context.get('active_ids')
            lead = self.env['crm.lead'].browse(lead_ids)
            vals.update({'lead_ids': lead, 'user_ids': [self.user_id.id]})
            self._convert_opportunity(vals)

        return lead[0].redirect_opportunity_view()

    def _create_partner(self, lead, action, partner_id):
        """
        Create partner based on action.
        :return dict: dictionary organized as followed: {lead_id: partner_assigned_id}
        """
        # TODO this method in only called by CrmLead2OpportunityPartner
        # wizard and would probably diserve to be refactored or at least
        # moved to a better place
        if self.action == 'each_exist_or_create':
            partner_id = self.with_context(
                active_id=lead.id)._find_matching_partner()
            action = 'create'
        res = lead.handle_partner_assignation(action, partner_id)
        return res.get(lead.id)


class CrmLead2OpportunityMassConvert(models.TransientModel):
    _name = 'crm.lead2opportunity.partner.mass'
    _description = 'Mass Lead To Opportunity Partner'
    _inherit = 'crm.lead2opportunity.partner'

    user_ids = fields.Many2many(
        'res.users', string='Salesmen', oldname='section_id')
    team_id = fields.Many2one('crm.team', string='Sales Team')
    deduplicate = fields.Boolean(
        string='Apply deduplication', help='Merge with existing leads/opportunities of each partner', default=True)
    action = fields.Selection([
        ('each_exist_or_create', 'Use existing partner or create'),
        ('nothing', 'Do not link to a customer')
    ], string='Related Customer', required=True)
    force_assignation = fields.Boolean(
        string='Force assignation', help='If unchecked, this will leave the salesman of duplicated opportunities')

    @api.model
    def default_get(self, fields):
        res = super(
            CrmLead2OpportunityMassConvert, self).default_get(fields)
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
    def on_change_action(self):
        if self.action != 'exist':
            self.partner_id = False

    @api.onchange('deduplicate')
    def on_change_deduplicate(self):
        leads = self.env['crm.lead'].browse(self.env.context['active_ids'])
        partner_ids = [(lead.partner_id.id, lead.partner_id.email or lead.email_from)
                       for lead in leads]
        partners_duplicated_leads = {}
        for partner_id, email in partner_ids:
            duplicated_leads = self._get_duplicated_leads(partner_id, email)
            if len(duplicated_leads) > 1:
                partners_duplicated_leads.setdefault((partner_id, email), []).extend(duplicated_leads.ids)
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
        salesteam_id = self.team_id.id
        salesmen_ids = []
        if self.user_ids:
            salesmen_ids = self.user_ids.ids
        vals.update({'user_ids': salesmen_ids, 'team_id': salesteam_id})
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
                    duplicated_lead_rec = self._get_duplicated_leads(
                        lead.partner_id.id, lead.partner_id.email or lead.email_from)
                    if len(duplicated_lead_rec.ids) > 1:
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
