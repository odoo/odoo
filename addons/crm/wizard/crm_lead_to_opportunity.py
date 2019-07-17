# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class Lead2OpportunityPartner(models.TransientModel):

    _name = 'crm.lead2opportunity.partner'
    _description = 'Convert Lead to Opportunity (not in mass)'
    _inherit = 'crm.partner.binding'

    @api.model
    def default_get(self, fields):
        """ Default get for name, opportunity_ids.
            If there is an exisitng partner link to the lead, find all existing
            opportunities links with this partner to merge all information together
        """
        result = super(Lead2OpportunityPartner, self).default_get(fields)
        if self._context.get('active_id'):
            tomerge = {int(self._context['active_id'])}

            partner_id = result.get('partner_id')
            lead = self.env['crm.lead'].browse(self._context['active_id'])
            email = lead.partner_id.email if lead.partner_id else lead.email_from

            tomerge.update(self._get_duplicated_leads(partner_id, email, include_lost=True).ids)

            if 'action' in fields and not result.get('action'):
                result['action'] = 'exist' if partner_id else 'create'
            if 'partner_id' in fields:
                result['partner_id'] = partner_id
            if 'name' in fields:
                result['name'] = 'merge' if len(tomerge) >= 2 else 'convert'
            if 'opportunity_ids' in fields and len(tomerge) >= 2:
                result['opportunity_ids'] = list(tomerge)
            if lead.user_id:
                result['user_id'] = lead.user_id.id
            if lead.team_id:
                result['team_id'] = lead.team_id.id
            if not partner_id and not lead.contact_name:
                result['action'] = 'nothing'
        return result

    name = fields.Selection([
        ('convert', 'Convert to opportunity'),
        ('merge', 'Merge with existing opportunities')
    ], 'Conversion Action', required=True)
    opportunity_ids = fields.Many2many('crm.lead', string='Opportunities')
    user_id = fields.Many2one('res.users', 'Salesperson', index=True)
    team_id = fields.Many2one('crm.team', 'Sales Team', oldname='section_id', index=True)

    @api.onchange('action')
    def onchange_action(self):
        if self.action == 'exist':
            self.partner_id = self._find_matching_partner()
        else:
            self.partner_id = False

    @api.onchange('user_id')
    def _onchange_user(self):
        """ When changing the user, also set a team_id or restrict team id
            to the ones user_id is member of.
        """
        if self.user_id:
            if self.team_id:
                user_in_team = self.env['crm.team'].search_count([('id', '=', self.team_id.id), '|', ('user_id', '=', self.user_id.id), ('member_ids', '=', self.user_id.id)])
            else:
                user_in_team = False
            if not user_in_team:
                values = self.env['crm.lead']._onchange_user_values(self.user_id.id if self.user_id else False)
                self.team_id = values.get('team_id', False)

    @api.model
    def _get_duplicated_leads(self, partner_id, email, include_lost=False):
        """ Search for opportunities that have the same partner and that arent done or cancelled """
        return self.env['crm.lead']._get_duplicated_leads_by_emails(partner_id, email, include_lost=include_lost)

    # NOTE JEM : is it the good place to test this ?
    @api.model
    def view_init(self, fields):
        """ Check some preconditions before the wizard executes. """
        for lead in self.env['crm.lead'].browse(self._context.get('active_ids', [])):
            if lead.probability == 100:
                raise UserError(_("Closed/Dead leads cannot be converted into opportunities."))
        return False

    def _convert_opportunity(self, vals):
        self.ensure_one()

        res = False

        leads = self.env['crm.lead'].browse(vals.get('lead_ids'))
        for lead in leads:
            self_def_user = self.with_context(default_user_id=self.user_id.id)
            partner_id = self_def_user._create_partner(
                lead.id, self.action, vals.get('partner_id') or lead.partner_id.id)
            res = lead.convert_opportunity(partner_id, [], False)
        user_ids = vals.get('user_ids')

        leads_to_allocate = leads
        if self._context.get('no_force_assignation'):
            leads_to_allocate = leads_to_allocate.filtered(lambda lead: not lead.user_id)

        if user_ids:
            leads_to_allocate.allocate_salesman(user_ids, team_id=(vals.get('team_id')))

        return res

    def action_apply(self):
        """ Convert lead to opportunity or merge lead and opportunity and open
            the freshly created opportunity view.
        """
        self.ensure_one()
        values = {
            'team_id': self.team_id.id,
        }

        if self.partner_id:
            values['partner_id'] = self.partner_id.id

        if self.name == 'merge':
            leads = self.with_context(active_test=False).opportunity_ids.merge_opportunity()
            if not leads.active:
                leads.write({'active': True, 'activity_type_id': False, 'lost_reason': False})
            if leads.type == "lead":
                values.update({'lead_ids': leads.ids, 'user_ids': [self.user_id.id]})
                self.with_context(active_ids=leads.ids)._convert_opportunity(values)
            elif not self._context.get('no_force_assignation') or not leads.user_id:
                values['user_id'] = self.user_id.id
                leads.write(values)
        else:
            leads = self.env['crm.lead'].browse(self._context.get('active_ids', []))
            values.update({'lead_ids': leads.ids, 'user_ids': [self.user_id.id]})
            self._convert_opportunity(values)

        return leads[0].redirect_opportunity_view()

    def _create_partner(self, lead_id, action, partner_id):
        """ Create partner based on action.
            :return dict: dictionary organized as followed: {lead_id: partner_assigned_id}
        """
        #TODO this method in only called by Lead2OpportunityPartner
        #wizard and would probably diserve to be refactored or at least
        #moved to a better place
        if action == 'each_exist_or_create':
            partner_id = self.with_context(active_id=lead_id)._find_matching_partner()
            action = 'create'
        result = self.env['crm.lead'].browse(lead_id).handle_partner_assignation(action, partner_id)
        return result.get(lead_id)


class Lead2OpportunityMassConvert(models.TransientModel):

    _name = 'crm.lead2opportunity.partner.mass'
    _description = 'Convert Lead to Opportunity (in mass)'
    _inherit = 'crm.lead2opportunity.partner'

    @api.model
    def default_get(self, fields):
        res = super(Lead2OpportunityMassConvert, self).default_get(fields)
        if 'partner_id' in fields:  # avoid forcing the partner of the first lead as default
            res['partner_id'] = False
        if 'action' in fields:
            res['action'] = 'each_exist_or_create'
        if 'name' in fields:
            res['name'] = 'convert'
        if 'opportunity_ids' in fields:
            res['opportunity_ids'] = False
        return res

    user_ids = fields.Many2many('res.users', string='Salesmen')
    team_id = fields.Many2one('crm.team', 'Sales Team', index=True, oldname='section_id')
    deduplicate = fields.Boolean('Apply deduplication', default=True, help='Merge with existing leads/opportunities of each partner')
    action = fields.Selection([
        ('each_exist_or_create', 'Use existing partner or create'),
        ('nothing', 'Do not link to a customer')
    ], 'Related Customer', required=True)
    force_assignation = fields.Boolean('Force assignation', help='If unchecked, this will leave the salesman of duplicated opportunities')

    @api.onchange('action')
    def _onchange_action(self):
        if self.action != 'exist':
            self.partner_id = False

    @api.onchange('deduplicate')
    def _onchange_deduplicate(self):
        active_leads = self.env['crm.lead'].browse(self._context['active_ids'])
        partner_ids = [(lead.partner_id.id, lead.partner_id and lead.partner_id.email or lead.email_from) for lead in active_leads]
        partners_duplicated_leads = {}
        for partner_id, email in partner_ids:
            duplicated_leads = self._get_duplicated_leads(partner_id, email)
            if len(duplicated_leads) > 1:
                partners_duplicated_leads.setdefault((partner_id, email), []).extend(duplicated_leads)

        leads_with_duplicates = []
        for lead in active_leads:
            lead_tuple = (lead.partner_id.id, lead.partner_id.email if lead.partner_id else lead.email_from)
            if len(partners_duplicated_leads.get(lead_tuple, [])) > 1:
                leads_with_duplicates.append(lead.id)

        self.opportunity_ids = self.env['crm.lead'].browse(leads_with_duplicates)

    def _convert_opportunity(self, vals):
        """ When "massively" (more than one at a time) converting leads to
            opportunities, check the salesteam_id and salesmen_ids and update
            the values before calling super.
        """
        self.ensure_one()
        salesteam_id = self.team_id.id if self.team_id else False
        salesmen_ids = []
        if self.user_ids:
            salesmen_ids = self.user_ids.ids
        vals.update({'user_ids': salesmen_ids, 'team_id': salesteam_id})
        return super(Lead2OpportunityMassConvert, self)._convert_opportunity(vals)

    def mass_convert(self):
        self.ensure_one()
        if self.name == 'convert' and self.deduplicate:
            merged_lead_ids = set()
            remaining_lead_ids = set()
            lead_selected = self._context.get('active_ids', [])
            for lead_id in lead_selected:
                if lead_id not in merged_lead_ids:
                    lead = self.env['crm.lead'].browse(lead_id)
                    duplicated_leads = self._get_duplicated_leads(lead.partner_id.id, lead.partner_id.email if lead.partner_id else lead.email_from)
                    if len(duplicated_leads) > 1:
                        lead = duplicated_leads.merge_opportunity()
                        merged_lead_ids.update(duplicated_leads.ids)
                        remaining_lead_ids.add(lead.id)
            active_ids = set(self._context.get('active_ids', {}))
            active_ids = (active_ids - merged_lead_ids) | remaining_lead_ids

            self = self.with_context(active_ids=list(active_ids))  # only update active_ids when there are set
        no_force_assignation = self._context.get('no_force_assignation', not self.force_assignation)
        return self.with_context(no_force_assignation=no_force_assignation).action_apply()
