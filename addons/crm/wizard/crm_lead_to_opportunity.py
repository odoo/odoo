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
        """ Default get for name, duplicated_lead_ids.
            If there is an exisitng partner link to the lead, find all existing
            opportunities links with this partner to merge all information together
        """
        result = super(Lead2OpportunityPartner, self).default_get(fields)
        if self._context.get('active_id'):
            tomerge = {int(self._context['active_id'])}

            lead = self.env['crm.lead'].browse(self._context['active_id'])
            result['lead_id'] = lead.id

            partner = lead._find_matching_partner()
            email = lead.partner_id.email if lead.partner_id else lead.email_from

            tomerge.update(self.env['crm.lead']._get_lead_duplicates(partner, email, include_lost=True).ids)

            if 'action' in fields and not result.get('action'):
                result['action'] = 'exist' if partner else 'create'
            if 'partner_id' in fields:
                result['partner_id'] = partner.id
            if 'name' in fields:
                result['name'] = 'merge' if len(tomerge) >= 2 else 'convert'
            if 'duplicated_lead_ids' in fields and len(tomerge) >= 2:
                result['duplicated_lead_ids'] = list(tomerge)
            if lead.user_id:
                result['user_id'] = lead.user_id.id
            if lead.team_id:
                result['team_id'] = lead.team_id.id
            if not partner and not lead.contact_name:
                result['action'] = 'nothing'

        return result

    name = fields.Selection([
        ('convert', 'Convert to opportunity'),
        ('merge', 'Merge with existing opportunities')
    ], 'Conversion Action', required=True)
    action = fields.Selection([
        ('create', 'Create a new customer'),
        ('exist', 'Link to an existing customer'),
        ('nothing', 'Do not link to a customer')
    ], string='Related Customer', required=True)
    lead_id = fields.Many2one('crm.lead', "Associated Lead")
    duplicated_lead_ids = fields.Many2many(
        'crm.lead', string='Duplicates', context={'active_test': False})
    partner_id = fields.Many2one('res.partner', 'Customer')
    user_id = fields.Many2one('res.users', 'Salesperson')
    team_id = fields.Many2one('crm.team', 'Sales Team')
    force_assignment = fields.Boolean(
        'Force assignment', default=True,
        help='If checked, forces salesman to be updated on updated opportunities even if already set.')

    @api.onchange('action')
    def onchange_action(self):
        if self.action == 'exist':
            self.partner_id = self.lead_id._find_matching_partner().id
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
    def view_init(self, fields):
        # JEM TDE FIXME: clean that brol
        """ Check some preconditions before the wizard executes. """
        for lead in self.env['crm.lead'].browse(self._context.get('active_ids', [])):
            if lead.probability == 100:
                raise UserError(_("Closed/Dead leads cannot be converted into opportunities."))
        return False

    def action_apply(self):
        if self.name == 'merge':
            result_opportunity = self._action_merge()
        else:
            result_opportunity = self._action_convert()

        return result_opportunity.redirect_lead_opportunity_view()

    def _action_merge(self):
        result_opportunity = self.duplicated_lead_ids.merge_opportunity()
        if not result_opportunity.active:
            result_opportunity.write({'active': True, 'activity_type_id': False, 'lost_reason': False})

        if result_opportunity.type == "lead":
            self._convert_and_allocate(result_opportunity, [self.user_id.id], team_id=self.team_id.id)
        else:
            if not result_opportunity.user_id or self.force_assignment:
                result_opportunity.write({
                    'user_id': self.user_id.id,
                    'team_id': self.team_id.id,
                })
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

            lead.convert_opportunity(lead.partner_id.id, [], False)

        leads_to_allocate = leads
        if not self.force_assignment:
            leads_to_allocate = leads_to_allocate.filtered(lambda lead: not lead.user_id)

        if user_ids:
            leads_to_allocate.handle_salesmen_assignment(user_ids, team_id=team_id)

    def _convert_handle_partner(self, lead, action, partner_id):
        # used to propagate user_id (salesman) on created partners during conversion
        lead.with_context(default_user_id=self.user_id.id).handle_partner_assignment(
            force_partner_id=partner_id,
            create_missing=(action == 'create')
        )
