# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.helpdesk.models.helpdesk_ticket import TICKET_PRIORITY


class HelpdeskSLA(models.Model):
    _name = "helpdesk.sla"
    _order = "name"
    _description = "Helpdesk SLA Policies"

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'team_id' in fields_list or 'stage_id' in fields_list:
            default_team_id = self._context.get('default_team_id')
            team = self.env['helpdesk.team'].browse(default_team_id)
            if not default_team_id:
                defaults['team_id'] = team.id
                team = self.env['helpdesk.team'].search([], limit=1)
            stages = team.stage_ids.filtered(lambda x: x.fold)
            defaults['stage_id'] = stages and stages.ids[0] or team.stage_ids and team.stage_ids.ids[-1]
        return defaults

    name = fields.Char(required=True, index=True, translate=True)
    description = fields.Html('SLA Policy Description', translate=True)
    active = fields.Boolean('Active', default=True)
    team_id = fields.Many2one('helpdesk.team', 'Helpdesk Team', required=True)
    tag_ids = fields.Many2many(
        'helpdesk.tag', string='Tags')
    stage_id = fields.Many2one(
        'helpdesk.stage', 'Target Stage',
        help='Minimum stage a ticket needs to reach in order to satisfy this SLA.')
    exclude_stage_ids = fields.Many2many(
        'helpdesk.stage', string='Excluding Stages', copy=True,
        domain="[('id', '!=', stage_id.id)]",
        help="The time spent in these stages won't be taken into account in the calculation of the SLA.")
    priority = fields.Selection(
        TICKET_PRIORITY, string='Priority',
        default='0', required=True)
    partner_ids = fields.Many2many(
        'res.partner', string="Customers")
    company_id = fields.Many2one('res.company', 'Company', related='team_id.company_id', readonly=True, store=True)
    time = fields.Float('Within', default=0, required=True,
        help='Maximum number of working hours a ticket should take to reach the target stage, starting from the date it was created.')
    ticket_count = fields.Integer(compute='_compute_ticket_count')

    def _compute_ticket_count(self):
        res = self.env['helpdesk.ticket']._read_group(
            [('sla_ids', 'in', self.ids), ('stage_id.fold', '=', False)],
            ['sla_ids'], ['__count'])
        sla_data = {sla.id: count for sla, count in res}
        for sla in self:
            sla.ticket_count = sla_data.get(sla.id, 0)

    @api.depends('team_id')
    @api.depends_context('with_team_name')
    def _compute_display_name(self):
        if not self._context.get('with_team_name'):
            return super()._compute_display_name()
        for sla in self:
            sla.display_name = f'{sla.name} - {sla.team_id.name}'

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=self.env._("%s (copy)", sla.name)) for sla, vals in zip(self, vals_list)]

    def action_open_helpdesk_ticket(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("helpdesk.helpdesk_ticket_action_main_tree")
        action.update({
            'domain': [('sla_ids', 'in', self.ids)],
            'context': {
                'search_default_is_open': True,
                'create': False,
            },
        })
        return action
