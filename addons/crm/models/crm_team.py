# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class Team(models.Model):
    _name = 'crm.team'
    _inherit = ['mail.alias.mixin', 'crm.team']

    resource_calendar_id = fields.Many2one('resource.calendar', string="Working Time", help="Used to compute open days")
    use_leads = fields.Boolean('Leads',
        help="The first contact you get with a potential customer is a lead you qualify before converting it into a real business opportunity. Check this box to manage leads in this sales team.")
    use_opportunities = fields.Boolean('Opportunities', default=True, help="Check this box to manage opportunities in this sales team.")
    alias_id = fields.Many2one('mail.alias', string='Alias', ondelete="restrict", required=True, help="The email address associated with this team. New emails received will automatically create new leads assigned to the team.")


    def get_alias_model_name(self, vals):
        return 'crm.lead'

    def get_alias_values(self):
        has_group_use_lead = self.env.user.has_group('crm.group_use_lead')
        values = super(Team, self).get_alias_values()
        values['alias_defaults'] = defaults = safe_eval(self.alias_defaults or "{}")
        defaults['type'] = 'lead' if has_group_use_lead and self.use_leads else 'opportunity'
        defaults['team_id'] = self.id
        return values

    @api.onchange('use_leads', 'use_opportunities')
    def _onchange_use_leads_opportunities(self):
        if not self.use_leads and not self.use_opportunities:
            self.alias_name = False

    @api.model
    def create(self, vals):
        generate_alias_name = self.env['ir.values'].get_default('sales.config.settings', 'generate_sales_team_alias')
        if generate_alias_name and not vals.get('alias_name'):
            vals['alias_name'] = vals.get('name')
        return super(Team, self).create(vals)

    @api.multi
    def write(self, vals):
        result = super(Team, self).write(vals)
        if 'use_leads' in vals or 'alias_defaults' in vals:
            for team in self:
                team.alias_id.write(team.get_alias_values())
        return result

    #TODO JEM : refactor this stuff with xml action, proper customization,
    @api.model
    def action_your_pipeline(self):
        action = self.env.ref('crm.crm_lead_opportunities_tree_view').read()[0]
        user_team_id = self.env.user.sale_team_id.id
        if not user_team_id:
            user_team_id = self.search([], limit=1).id
            action['help'] = """<p class='oe_view_nocontent_create'>Click here to add new opportunities</p><p>
    Looks like you are not a member of a sales team. You should add yourself
    as a member of one of the sales team.
</p>"""
            if user_team_id:
                action['help'] += "<p>As you don't belong to any sales team, Odoo opens the first one by default.</p>"

        action_context = safe_eval(action['context'], {'uid': self.env.uid})
        if user_team_id:
            action_context['default_team_id'] = user_team_id

        tree_view_id = self.env.ref('crm.crm_case_tree_view_oppor').id
        form_view_id = self.env.ref('crm.crm_case_form_view_oppor').id
        kanb_view_id = self.env.ref('crm.crm_case_kanban_view_leads').id
        action['views'] = [
                [kanb_view_id, 'kanban'],
                [tree_view_id, 'tree'],
                [form_view_id, 'form'],
                [False, 'graph'],
                [False, 'calendar'],
                [False, 'pivot']
            ]
        action['context'] = action_context
        return action
