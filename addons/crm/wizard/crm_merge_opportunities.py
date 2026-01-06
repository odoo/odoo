# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class CrmMergeOpportunity(models.TransientModel):
    """
        Merge opportunities together.
        If we're talking about opportunities, it's just because it makes more sense
        to merge opps than leads, because the leads are more ephemeral objects.
        But since opportunities are leads, it's also possible to merge leads
        together (resulting in a new lead), or leads and opps together (resulting
        in a new opp).
    """

    _name = 'crm.merge.opportunity'
    _description = 'Merge Opportunities'

    @api.model
    def default_get(self, fields):
        """ Use active_ids from the context to fetch the leads/opps to merge.
        In order to get merged, these leads/opps cannot be already 'Won' (closed)
        """
        record_ids = self.env.context.get('active_ids')
        result = super().default_get(fields)

        if record_ids:
            if 'opportunity_ids' in fields:
                opp_ids = self.env['crm.lead'].browse(record_ids).filtered(lambda opp: opp.won_status != 'won').ids
                result['opportunity_ids'] = [(6, 0, opp_ids)]

        return result

    opportunity_ids = fields.Many2many(
        'crm.lead', 'merge_opportunity_rel', 'merge_id', 'opportunity_id',
        string='Leads/Opportunities',
        context={'active_test': False})
    user_id = fields.Many2one(
        'res.users', 'Salesperson', domain="[('share', '=', False)]",
        compute='_compute_user_id', readonly=False, store=True)
    team_id = fields.Many2one(
        'crm.team', 'Sales Team',
        compute='_compute_team_id', readonly=False, store=True)

    @api.depends('user_id')
    def _compute_team_id(self):
        """ When changing the user, also set a team_id or restrict team id
            to the ones user_id is member of. """
        for wizard in self:
            if wizard.user_id:
                user_in_team = False
                if wizard.team_id:
                    user_in_team = wizard.env['crm.team'].search_count([('id', '=', wizard.team_id.id), '|', ('user_id', '=', wizard.user_id.id), ('member_ids', '=', wizard.user_id.id)])
                if not user_in_team:
                    wizard.team_id = wizard.env['crm.team'].search(['|', ('user_id', '=', wizard.user_id.id), ('member_ids', '=', wizard.user_id.id)], limit=1)                    

    @api.depends('opportunity_ids')
    def _compute_user_id(self):
        for wizard in self:
            wizard.user_id = wizard.opportunity_ids.user_id if len(wizard.opportunity_ids.user_id) == 1 else False

    def action_merge(self):
        merged = self._action_merge_to_opportunity()
        if not merged:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Something went wrong, please try again later'),
                    'type': 'warning',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                },
            }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Leads merged'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def _action_merge_to_opportunity(self):
        self.ensure_one()
        return self.opportunity_ids.merge_opportunity(self.user_id.id, self.team_id.id)
