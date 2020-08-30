# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Lead2OpportunityMassConvert(models.TransientModel):
    _name = 'crm.lead2opportunity.partner.mass'
    _description = 'Convert Lead to Opportunity (in mass)'
    _inherit = 'crm.lead2opportunity.partner'

    lead_id = fields.Many2one(required=False)
    lead_tomerge_ids = fields.Many2many(
        'crm.lead', 'crm_convert_lead_mass_lead_rel',
        string='Active Leads', context={'active_test': False},
        default=lambda self: self.env.context.get('active_ids', []),
    )
    user_ids = fields.Many2many('res.users', string='Salespersons')
    deduplicate = fields.Boolean('Apply deduplication', default=True, help='Merge with existing leads/opportunities of each partner')
    action = fields.Selection(selection_add=[
        ('each_exist_or_create', 'Use existing partner or create'),
    ], string='Related Customer', ondelete={
        'each_exist_or_create': lambda recs: recs.write({'action': 'exist'}),
    })
    force_assignment = fields.Boolean(default=False)

    @api.depends('duplicated_lead_ids')
    def _compute_name(self):
        for convert in self:
            convert.name = 'convert'

    @api.depends('lead_tomerge_ids')
    def _compute_action(self):
        for convert in self:
            convert.action = 'each_exist_or_create'

    @api.depends('lead_tomerge_ids')
    def _compute_partner_id(self):
        for convert in self:
            convert.partner_id = False

    @api.depends('user_ids')
    def _compute_team_id(self):
        """ When changing the user, also set a team_id or restrict team id
        to the ones user_id is member of. """
        for convert in self:
            # setting user as void should not trigger a new team computation
            if not convert.user_id and not convert.user_ids and convert.team_id:
                continue
            user = convert.user_id or convert.user_ids and convert.user_ids[0] or self.env.user
            if convert.team_id and user in convert.team_id.member_ids | convert.team_id.user_id:
                continue
            team_domain = []
            team = self.env['crm.team']._get_default_team_id(user_id=user.id, domain=team_domain)
            convert.team_id = team.id

    @api.depends('lead_tomerge_ids')
    def _compute_duplicated_lead_ids(self):
        for convert in self:
            duplicated = self.env['crm.lead']
            for lead in convert.lead_tomerge_ids:
                duplicated_leads = self.env['crm.lead']._get_lead_duplicates(
                    partner=lead.partner_id,
                    email=lead.partner_id and lead.partner_id.email or lead.email_from,
                    include_lost=False)
                if len(duplicated_leads) > 1:
                    duplicated += lead
            convert.duplicated_lead_ids = duplicated.ids

    def _convert_and_allocate(self, leads, user_ids, team_id=False):
        """ When "massively" (more than one at a time) converting leads to
        opportunities, check the salesteam_id and salesmen_ids and update
        the values before calling super.
        """
        self.ensure_one()
        salesmen_ids = []
        if self.user_ids:
            salesmen_ids = self.user_ids.ids
        return super(Lead2OpportunityMassConvert, self)._convert_and_allocate(leads, salesmen_ids, team_id=team_id)

    def action_mass_convert(self):
        self.ensure_one()
        if self.name == 'convert' and self.deduplicate:
            merged_lead_ids = set()
            remaining_lead_ids = set()
            for lead in self.lead_tomerge_ids:
                if lead not in merged_lead_ids:
                    duplicated_leads = self.env['crm.lead']._get_lead_duplicates(
                        partner=lead.partner_id,
                        email=lead.partner_id.email or lead.email_from,
                        include_lost=False
                    )
                    if len(duplicated_leads) > 1:
                        lead = duplicated_leads.merge_opportunity()
                        merged_lead_ids.update(duplicated_leads.ids)
                        remaining_lead_ids.add(lead.id)
            active_ids = set(self._context.get('active_ids', {}))
            active_ids = (active_ids - merged_lead_ids) | remaining_lead_ids

            self = self.with_context(active_ids=list(active_ids))  # only update active_ids when there are set
        return self.action_apply()

    def _convert_handle_partner(self, lead, action, partner_id):
        if self.action == 'each_exist_or_create':
            partner_id = lead._find_matching_partner(email_only=True).id
            action = 'create'
        return super(Lead2OpportunityMassConvert, self)._convert_handle_partner(lead, action, partner_id)
