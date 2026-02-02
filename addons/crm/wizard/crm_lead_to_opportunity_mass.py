# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class CrmLead2opportunityPartnerMass(models.TransientModel):
    _name = 'crm.lead2opportunity.partner.mass'
    _description = 'Convert Lead to Opportunity (in mass)'

    action = fields.Selection([
        ('create', 'Link to new/matching customer(s)'),
        ('do_not_link', 'Do not link to customers'),
        ('exist', 'Link to specific customer'),
    ], string='Related Customer', default='create', required=True)
    # the duplicated_lead_ids field stores those leads from the selected `active_ids` which have any duplicates
    duplicated_lead_ids = fields.Many2many(
        'crm.lead', string='Opportunities', context={'active_test': False},
        compute='_compute_duplicated_lead_ids', store=True, compute_sudo=False)
    # the found_duplicates field stores all the found duplicates, to be displayed in the dialog
    found_duplicates_ids = fields.Many2many(
        'crm.lead', 'lead2opp_mass_dup_lead_copies_rel', 'wizard_id', 'lead_id',
        context={'active_test': False}, compute='_compute_duplicated_lead_ids', store=True, compute_sudo=False)
    force_assignment = fields.Boolean(
        'Force assignment', default=False,
        help='If checked, forces salesman to be updated on updated opportunities even if already set.')
    lead_count_message = fields.Char('Lead Count', compute='_compute_lead_count_message')
    lead_tomerge_ids = fields.Many2many(
        'crm.lead', 'crm_convert_lead_mass_lead_rel',
        string='Active Leads', context={'active_test': False},
        default=lambda self: self.env.context.get('active_ids', []),
    )
    name = fields.Selection([
        ('convert', 'Convert to Opportunities'),
        ('convert_and_merge', 'Convert & Merge with Opportunities'),
        ('deduplicate', 'Deduplicate leads')
    ], 'Conversion Action', default='convert', readonly=False)
    partner_id = fields.Many2one('res.partner', 'Customer')
    team_id = fields.Many2one('crm.team', 'Sales Team', compute='_compute_team_id',
        readonly=False, store=True, compute_sudo=False)
    user_ids = fields.Many2many('res.users', string='Salespersons')

    @api.depends('lead_tomerge_ids')
    def _compute_lead_count_message(self):
        for convert in self:
            selected_duplicate_count = len(convert.duplicated_lead_ids)
            convert.lead_count_message = _(
                "Found potential duplicates for %(selected_duplicate_count)s of the leads you have selected. "
                'Choose a "Convert & Merge" or "Deduplicate" deduplication option to clean your data before converting',
                selected_duplicate_count=selected_duplicate_count)

    @api.depends('user_ids')
    def _compute_team_id(self):
        """ When changing the user, also set a team_id or restrict team id
        to the ones user_id is member of. """
        for convert in self:
            # setting users as void should not trigger a new team computation
            if not convert.user_ids:
                continue
            user = convert.user_ids and convert.user_ids[0] or self.env.user
            if convert.team_id and user in convert.team_id.member_ids | convert.team_id.user_id:
                continue
            team = self.env['crm.team']._get_default_team_id(user_id=user.ids[0], domain=None)
            convert.team_id = team.id

    @api.depends('lead_tomerge_ids')
    def _compute_duplicated_lead_ids(self):
        for convert in self:
            duplicated = self.env['crm.lead']
            all_duplicates = self.env['crm.lead']
            for lead in convert.lead_tomerge_ids:
                duplicate_leads = self.env['crm.lead']._get_lead_duplicates(
                    partner=lead.partner_id,
                    email=lead.partner_id and lead.partner_id.email or lead.email_from,
                    include_lost=False)
                if len(duplicate_leads) > 1:
                    duplicated += lead
                    all_duplicates += duplicate_leads

            convert.duplicated_lead_ids = duplicated.ids
            convert.found_duplicates_ids = all_duplicates.ids

    def action_apply(self):
        if self.name == 'deduplicate':
            result_opportunity = self._action_deduplicate()
        elif self.name == 'convert_and_merge':
            result_opportunity = self._action_convert_and_merge()
        else:
            result_opportunity = self._action_convert()

        return result_opportunity.redirect_lead_opportunity_view()

    def _action_deduplicate(self):
        """Convert and deduplicate leads, returning the result opportunity."""
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

        # rebuild list of lead IDS, following given order
        final_ids = [lead_id for lead_id in self.lead_tomerge_ids.ids if lead_id not in merged_lead_ids]
        final_ids += [lead_id for lead_id in remaining_lead_ids if lead_id not in final_ids]
        # What should deduplicate return? Return one of the leads or just close the dialog with a success toast?
        return self.env['crm.lead'].browse(final_ids[0])

    def _action_convert_and_merge(self):
        """Convert all selected leads, if any of them have a matching existing opportunity,
        merge it and return the result opportunity."""
        final_leads = self.env['crm.lead']
        to_convert = self.env['crm.lead']

        for lead in self.lead_tomerge_ids:
            duplicate_opportunities = self.env['crm.lead']._get_lead_duplicates(
                partner=lead.partner_id,
                email=lead.partner_id and lead.partner_id.email or lead.email_from,
                include_lost=False).filtered(lambda l: l.type == 'opportunity')

            # Merge with matching existing opportunity
            if len(duplicate_opportunities) != 0:
                result_opportunity = (duplicate_opportunities + lead).merge_opportunity()
            else:
                result_opportunity = lead
                to_convert += result_opportunity

            result_opportunity.action_unarchive()
            final_leads += result_opportunity

        # Convert leads that weren't merged with opportunities
        self._convert_and_allocate(to_convert)

        return final_leads[0]

    def _action_convert(self):
        result_opportunities = self.env['crm.lead'].browse(self.env.context.get('active_ids', []))
        self._convert_and_allocate(result_opportunities)
        return result_opportunities[0]

    def _convert_and_allocate(self, leads):
        for lead in leads:
            if lead.active:
                self._convert_handle_partner(
                    lead, self.action, self.partner_id.id or lead.partner_id.id)

                lead.convert_opportunity(lead.partner_id, user_ids=False, team_id=False)

        if self.user_ids:
            leads_to_allocate = leads if self.force_assignment else leads.filtered(lambda l: not l.user_id)
            leads_to_allocate._handle_salesmen_assignment(self.user_ids.ids, team_id=self.team_id.id)

    def _convert_handle_partner(self, lead, action, partner_id):
        if self.action == 'create':
            partner_id = lead._find_matching_partner().id

        if self.action == 'do_not_link':
            # reset partner_id in case the user set the field, then switched back to do_not_link
            partner_id = False

        lead._handle_partner_assignment(
            force_partner_id=partner_id,
            create_missing=action == 'create',
        )
