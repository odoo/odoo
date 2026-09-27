# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class CrmLead2opportunityPartnerMass(models.TransientModel):
    _name = 'crm.lead2opportunity.partner.mass'
    _description = 'Convert Lead to Opportunity (in mass)'

    duplicated_lead_ids = fields.Many2many(
        'crm.lead', context={'active_test': False}, compute='_compute_duplicated_lead_ids',
        store=True, compute_sudo=False, readonly=False)
    duplicated_lead_ids_domain = fields.Many2many(
        'crm.lead', 'crm_lead_duplicate_domain_rel', context={'active_test': False},
        compute='_compute_duplicated_lead_ids', store=True, compute_sudo=False)
    force_assignment = fields.Boolean('Even if assigned')
    lead_tomerge_ids = fields.Many2many(
        'crm.lead', 'crm_convert_lead_mass_lead_rel',
        string='Active Leads', context={'active_test': False},
        default=lambda self: self.env.context.get('active_ids', [])
    )
    link_to_matching_customer = fields.Boolean(string="Link to matching customers",
        help="Link these opportunities to customers by either finding a match or creating a new one.")
    name = fields.Selection([
        ('convert', 'Convert to Opportunities'),
        ('convert_and_merge', 'Convert & Merge with Opportunities'),
    ], 'Conversion Action', default='convert', readonly=False, required=True)
    team_id = fields.Many2one('crm.team', 'Sales Team', compute='_compute_team_id',
        readonly=False, store=True, compute_sudo=False)
    user_ids = fields.Many2many('res.users', string='Salespersons')

    @api.depends('lead_tomerge_ids')
    def _compute_duplicated_lead_ids(self):
        for convert in self:
            all_duplicates = self.env['crm.lead']
            for lead in convert.lead_tomerge_ids:
                if lead in all_duplicates:
                    continue

                duplicate_leads = self.env['crm.lead']._get_lead_duplicates(
                    partner=lead.partner_id,
                    email=lead.partner_id and lead.partner_id.email or lead.email_from,
                    include_lost=False,
                )
                if len(duplicate_leads) > 1:
                    all_duplicates |= duplicate_leads

            convert.duplicated_lead_ids = all_duplicates.ids
            convert.duplicated_lead_ids_domain = all_duplicates.ids

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

    @api.onchange('duplicated_lead_ids')
    def _onchange_duplicated_lead_ids(self):
        if not self.duplicated_lead_ids:
            self.name = 'convert'

    def action_apply(self):
        affected_leads_count = len(self.lead_tomerge_ids.filtered(lambda l: l.active))
        if self.name == 'convert_and_merge':
            affected_leads_count = self._action_convert_and_merge()
        else:
            self._convert_and_allocate(self.lead_tomerge_ids)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success" if affected_leads_count else "warning",
                "message": self._get_success_toast_message(affected_leads_count),
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _get_success_toast_message(self, affected_leads_count):
        if affected_leads_count == 1:
            return _("1 lead has been converted")
        else:
            return _("%(converted_count)s leads have been converted", converted_count=affected_leads_count)

    def _action_convert_and_merge(self):
        """
        Convert all selected leads. If any of them have duplicates that were not removed by the user, merge them.
        Always merge the initially selected leads, even if they were removed from the list.

        returns: number of converted/merged leads.
        """
        merge_result_opportunity_ids = self.env['crm.lead']
        affected_leads_count = 0

        for lead in self.lead_tomerge_ids:
            if not lead.exists() or lead.id in merge_result_opportunity_ids.ids:
                continue

            # Because we don't store a mapping of each opportunity to it's duplicate, we recompute the duplicates
            # when the user submits the form. To apply the user's changes, we perform a union with the stored list
            # of opportunities from which the user can remove records
            duplicate_leads = self.env['crm.lead']._get_lead_duplicates(
                partner=lead.partner_id,
                email=lead.partner_id and lead.partner_id.email or lead.email_from,
                include_lost=False,
            ) & self.duplicated_lead_ids

            affected_leads_count += len(duplicate_leads)
            if len(duplicate_leads) > 1:  # Merge remaining leads together
                merge_result_opportunity_ids |= duplicate_leads.merge_opportunity()
            elif len(duplicate_leads) == 1:  # `merge_opportunities` needs at least 2 leads -> add to the result to be converted later
                merge_result_opportunity_ids |= duplicate_leads

            # Allways convert the lead from the initial selection, even if removed from the list
            if lead not in duplicate_leads and lead.exists():
                merge_result_opportunity_ids |= lead
                if lead.active:
                    affected_leads_count += 1

        # Convert remaining leads that weren't merged with opportunities
        self._convert_and_allocate(merge_result_opportunity_ids.filtered(lambda l: l.type != 'opportunity'))
        return affected_leads_count

    def _convert_and_allocate(self, leads):
        for lead in leads:
            if lead.active:
                self._convert_handle_partner(lead, lead.partner_id.id)
                lead.convert_opportunity(lead.partner_id, user_ids=False, team_id=False)

        if self.user_ids:
            leads_to_allocate = leads if self.force_assignment else leads.filtered(lambda l: not l.user_id)
            leads_to_allocate._handle_salesmen_assignment(self.user_ids.ids, team_id=self.team_id.id)

    def _convert_handle_partner(self, lead, partner_id):
        if self.link_to_matching_customer:
            partner_id = lead._find_matching_partner().id

        lead._handle_partner_assignment(
            force_partner_id=partner_id,
            create_missing=self.link_to_matching_customer,
        )
