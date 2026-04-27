# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.osv import expression


class SlideChannel(models.Model):
    _inherit = 'slide.channel'

    helpdesk_team_ids = fields.Many2many('helpdesk.team', 'helpdesk_team_slide_channel_rel', 'slide_channel_id', 'helpdesk_team_id')
    helpdesk_team_count = fields.Integer('Helpdesk Team Count', compute='_compute_helpdesk_team_count', export_string_translation=False)

    @api.depends('helpdesk_team_ids')
    def _compute_helpdesk_team_count(self):
        for team in self:
            team.helpdesk_team_count = len(team.helpdesk_team_ids)

    @api.model
    def _search_get_detail(self, website, order, options):
        res = super()._search_get_detail(website, order, options)

        team = self.env['helpdesk.team']
        if options.get('helpdesk'):
            team = team.browse(self.env['ir.http']._unslug(options['helpdesk'])[1])

        if not team:
            return res

        extra_domain = []
        if options.get('tag'):
            extra_domain = [('tag_ids.name', 'ilike', options['tag'])]
        website_slide_channel_ids = team.sudo().website_slide_channel_ids
        if website_slide_channel_ids:
            extra_domain = expression.AND([[('id', 'in', website_slide_channel_ids.ids)], extra_domain])
        res['base_domain'] = [res['base_domain'][0] + extra_domain]

        return res

    def action_view_helpdesk_teams(self):
        self.ensure_one()
        action_window = {
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.team',
            'name': _("%(name)s's Helpdesk Teams", name=self.name),
            'context': {
                'default_use_website_helpdesk_form': True,
                'default_use_website_helpdesk_slides': True,
                'default_website_slide_channel_ids': [self.id],
            }

        }
        if self.helpdesk_team_count == 1:
            action_window.update({
                "res_id": self.helpdesk_team_ids.id,
                "views": [(False, 'form')],
            })
        else:
            action_window.update({
                "domain": [('id', 'in', self.helpdesk_team_ids.ids)],
                "views": [(False, 'list'), (False, 'form'), (False, 'kanban')],
            })
        return action_window
