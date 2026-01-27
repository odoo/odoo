# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class CrmLead2opportunityPartnerMass(models.TransientModel):
    _name = 'crm.lead2opportunity.partner.mass'
    _description = 'Convert Lead to Opportunity (in mass)'
    _inherit = ['crm.lead2opportunity.partner']

    force_assignment = fields.Boolean(default=False)
    lead_count_message = fields.Char('Lead Count', compute='_compute_lead_count_message', readonly=True)
    lead_id = fields.Many2one(required=False)
    lead_tomerge_ids = fields.Many2many(
        'crm.lead', 'crm_convert_lead_mass_lead_rel',
        string='Active Leads', context={'active_test': False},
        default=lambda self: self.env.context.get('active_ids', []),
    )
    name = fields.Selection(selection_add=[('convert_and_deduplicate', 'Convert & deduplicate')],
                            ondelete={'convert_and_deduplicate': 'set convert_and_merge'})
    user_ids = fields.Many2many('res.users', string='Salespersons')

    @api.depends('lead_tomerge_ids')
    def _compute_lead_count_message(self):
        for convert in self:
            count = len(convert.lead_tomerge_ids)
            duplicate_count = len(convert.duplicated_lead_ids)
            if count == 1:
                convert.lead_count_message = _("Found %(duplicate_count)s potential duplicate(s) with your selected lead. Choose a deduplication option to clean your data before converting", duplicate_count=duplicate_count)
            else:
                convert.lead_count_message = _("Found %(duplicate_count)s potential duplicates within your %(count)s selected leads. Choose a deduplication option to clean your data before converting", count=count, duplicate_count=duplicate_count)

    @api.depends('lead_tomerge_ids')
    def _compute_action(self):
        for convert in self:
            convert.action = 'create'

    @api.depends('lead_tomerge_ids')
    def _compute_partner_id(self):
        for convert in self:
            convert.partner_id = False

    def _compute_commercial_partner_id(self):
        """Setting a company for each lead in mass mode is not supported."""
        self.commercial_partner_id = False

    def _compute_user_id(self):
        for convert in self:
            convert.user_id = False

    @api.depends('lead_id', 'user_ids')
    def _compute_team_id(self):
        """ When changing the user, also set a team_id or restrict team id
        to the ones user_id is member of. """
        for convert in self:
            # setting user as void should not trigger a new team computation
            if not convert.user_id and not convert.user_ids:
                continue
            user = convert.user_id or convert.user_ids and convert.user_ids[0] or self.env.user
            if convert.team_id and user in convert.team_id.member_ids | convert.team_id.user_id:
                continue
            elif user in convert.lead_id.team_id.member_ids | convert.lead_id.team_id.user_id:
                convert.team_id = convert.lead_id.team_id
                continue
            team = self.env['crm.team']._get_default_team_id(user_id=user.id, domain=None)
            convert.team_id = team.id

    @api.depends('lead_tomerge_ids')
    def _compute_duplicated_lead_ids(self):
        for convert in self:
            duplicated = self.env['crm.lead']
            for lead in convert.lead_tomerge_ids:
                duplicate_leads = self.env['crm.lead']._get_lead_duplicates(
                    partner=lead.partner_id,
                    email=lead.partner_id and lead.partner_id.email or lead.email_from,
                    include_lost=False)
                if len(duplicate_leads) > 1:
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
        return super()._convert_and_allocate(leads, salesmen_ids, team_id=team_id)

    def action_mass_convert(self):
        self.ensure_one()
        if self.name == 'convert_and_deduplicate':
            # TDE CLEANME: still using active_ids from context
            active_ids = self.env.context.get('active_ids', [])
            merged_lead_ids = set()
            remaining_lead_ids = set()
            for lead in self.lead_tomerge_ids:
                if lead.id not in merged_lead_ids:
                    duplicated_leads = self.env['crm.lead']._get_lead_duplicates(
                        partner=lead.partner_id,
                        email=lead.partner_id.email or lead.email_from,
                        include_lost=False
                    )
                    if len(duplicated_leads) > 1:
                        lead = duplicated_leads.merge_opportunity()
                        merged_lead_ids.update(duplicated_leads.ids)
                        remaining_lead_ids.add(lead.id)
            # rebuild list of lead IDS to convert, following given order
            final_ids = [lead_id for lead_id in active_ids if lead_id not in merged_lead_ids]
            final_ids += [lead_id for lead_id in remaining_lead_ids if lead_id not in final_ids]

            self = self.with_context(active_ids=final_ids)  # only update active_ids when there are set
        return self.action_apply()

    def _convert_handle_partner(self, lead, action, partner_id):
        if self.action == 'create':
            partner_id = lead._find_matching_partner().id
        return super()._convert_handle_partner(lead, action, partner_id)
