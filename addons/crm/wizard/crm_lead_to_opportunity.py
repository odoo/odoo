# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class Lead2OpportunityPartner(models.TransientModel):
    _name = 'crm.lead2opportunity.partner'
    _description = 'Convert Lead to Opportunity (not in mass)'

    @api.model
    def default_get(self, fields):
        """ Allow support of active_id / active_model instead of jut default_lead_id
        to ease window action definitions, and be backward compatible. """
        result = super(Lead2OpportunityPartner, self).default_get(fields)

        if not result.get('lead_id') and self.env.context.get('active_id'):
            result['lead_id'] = self.env.context.get('active_id')

        if result.get('lead_id'):
            if self.env['crm.lead'].browse(result['lead_id']).probability == 100:
                raise UserError(_("Closed/Dead leads cannot be converted into opportunities."))

        return result

    name = fields.Selection([
        ('convert', 'Convert to opportunity'),
        ('merge', 'Merge with existing opportunities')
    ], 'Conversion Action', compute='_compute_name', readonly=False, store=True, compute_sudo=False)
    action = fields.Selection([
        ('create', 'Create a new customer'),
        ('exist', 'Link to an existing customer'),
        ('nothing', 'Do not link to a customer')
    ], string='Related Customer', compute='_compute_action', readonly=False, store=True, compute_sudo=False)
    lead_id = fields.Many2one('crm.lead', 'Associated Lead', required=True)
    duplicated_lead_ids = fields.Many2many(
        'crm.lead', string='Opportunities', context={'active_test': False},
        compute='_compute_duplicated_lead_ids', readonly=False, store=True, compute_sudo=False)
    partner_id = fields.Many2one(
        'res.partner', 'Customer',
        compute='_compute_partner_id', readonly=False, store=True, compute_sudo=False)
    user_id = fields.Many2one(
        'res.users', 'Salesperson',
        compute='_compute_user_id', readonly=False, store=True, compute_sudo=False)
    team_id = fields.Many2one(
        'crm.team', 'Sales Team',
        compute='_compute_team_id', readonly=False, store=True, compute_sudo=False)
    force_assignment = fields.Boolean(
        'Force assignment', default=True,
        help='If checked, forces salesman to be updated on updated opportunities even if already set.')

    @api.depends('duplicated_lead_ids')
    def _compute_name(self):
        for convert in self:
            if not convert.name:
                convert.name = 'merge' if convert.duplicated_lead_ids and len(convert.duplicated_lead_ids) >= 2 else 'convert'

    @api.depends('lead_id')
    def _compute_action(self):
        for convert in self:
            if not convert.lead_id:
                convert.action = 'nothing'
            else:
                partner = convert.lead_id._find_matching_partner()
                if partner:
                    convert.action = 'exist'
                elif convert.lead_id.contact_name:
                    convert.action = 'create'
                else:
                    convert.action = 'nothing'

    @api.depends('lead_id', 'partner_id')
    def _compute_duplicated_lead_ids(self):
        for convert in self:
            if not convert.lead_id:
                convert.duplicated_lead_ids = False
                continue
            convert.duplicated_lead_ids = self.env['crm.lead']._get_lead_duplicates(
                convert.partner_id,
                convert.lead_id.partner_id.email if convert.lead_id.partner_id.email else convert.lead_id.email_from,
                include_lost=True).ids

    @api.depends('action', 'lead_id')
    def _compute_partner_id(self):
        for convert in self:
            if convert.action == 'exist':
                convert.partner_id = convert.lead_id._find_matching_partner()
            else:
                convert.partner_id = False

    @api.depends('lead_id')
    def _compute_user_id(self):
        for convert in self:
            convert.user_id = convert.lead_id.user_id if convert.lead_id.user_id else False

    @api.depends('user_id')
    def _compute_team_id(self):
        """ When changing the user, also set a team_id or restrict team id
        to the ones user_id is member of. """
        for convert in self:
            # setting user as void should not trigger a new team computation
            if not convert.user_id:
                continue
            user = convert.user_id
            if convert.team_id and user in convert.team_id.member_ids | convert.team_id.user_id:
                continue
            team = self.env['crm.team']._get_default_team_id(user_id=user.id, domain=None)
            convert.team_id = team.id

    def action_apply(self):
        if self.name == 'merge':
            result_opportunity = self._action_merge()
        else:
            result_opportunity = self._action_convert()

        return result_opportunity.redirect_lead_opportunity_view()

    def _action_merge(self):
        to_merge = self.duplicated_lead_ids
        result_opportunity = to_merge.merge_opportunity(auto_unlink=False)
        result_opportunity.action_unarchive()

        if result_opportunity.type == "lead":
            self._convert_and_allocate(result_opportunity, [self.user_id.id], team_id=self.team_id.id)
        else:
            if not result_opportunity.user_id or self.force_assignment:
                result_opportunity.write({
                    'user_id': self.user_id.id,
                    'team_id': self.team_id.id,
                })
        if self.lead_id != result_opportunity:
            # Prevent unwanted cascade during unlinks, keeping other operations and overrides possible
            self.write({'lead_id': result_opportunity})
        (to_merge - result_opportunity).sudo().unlink()
        return result_opportunity

    def _action_convert(self):
        """ """
        result_opportunities = self.env['crm.lead'].browse(self._context.get('active_ids', []))
        self._convert_and_allocate(result_opportunities, [self.user_id.id], team_id=self.team_id.id)
        return result_opportunities[0]

    def _convert_and_allocate(self, leads, user_ids, team_id=False):
        self.ensure_one()

        for lead in leads:
            if lead.active and self.action != 'nothing':
                self._convert_handle_partner(
                    lead, self.action, self.partner_id.id or lead.partner_id.id)

            lead.convert_opportunity(lead.partner_id, user_ids=False, team_id=False)

        leads_to_allocate = leads
        if not self.force_assignment:
            leads_to_allocate = leads_to_allocate.filtered(lambda lead: not lead.user_id)

        if user_ids:
            leads_to_allocate._handle_salesmen_assignment(user_ids, team_id=team_id)

    def _convert_handle_partner(self, lead, action, partner_id):
        # used to propagate user_id (salesman) on created partners during conversion
        lead.with_context(default_user_id=self.user_id.id)._handle_partner_assignment(
            force_partner_id=partner_id,
            create_missing=(action == 'create')
        )
