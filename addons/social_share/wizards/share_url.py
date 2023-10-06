# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import secrets

from odoo import api, fields, models
from ..controllers.main import EventSharePostController


class SocialShareUrlShare(models.TransientModel):
    _name = 'social.share.url.share'

    campaign_id = fields.Many2one('social.share.post')
    model_id = fields.Many2one('ir.model', related='campaign_id.model_id')
    target_id = fields.Reference(selection='_selection_target_id')
    message = fields.Char('Thank-You message')
    url_id = fields.Many2one('social.share.url', compute='_compute_url_id', string="Url Resolver")
    url = fields.Char(compute='_compute_url')

    def _selection_target_id(self):
        groups = self.env['social.share.post']._read_group(
            domain=[('model_id', '!=', False)],
            groupby=['model_id'],
        )
        return [(model.model, model.display_name) for model, *_ in groups]

    @api.depends('campaign_id', 'target_id')
    def _compute_url_id(self):
        for share_wizard in self:
            if not share_wizard.model_id or not share_wizard.target_id:
                share_wizard.url_id = False
                continue
            url_id = self.env['social.share.url'].sudo().search([
                ('campaign_id', '=', share_wizard.campaign_id.id),
                ('target_id', '=', share_wizard.target_id.id)
            ])
            if not url_id:
                url_id = self.env['social.share.url'].sudo().create({
                    'campaign_id': share_wizard.campaign_id.id,
                    'target_id': share_wizard.target_id.id
                })
            share_wizard.url_id = url_id

    @api.depends('url_id', 'campaign_id')
    def _compute_url(self):
        for share_wizard in self:
            uuid = share_wizard.url_id.uuid if share_wizard.model_id else ''
            share_wizard.url = EventSharePostController._get_post_url(
                share_wizard.campaign_id.id, uuid
            )

    def action_apply_to_url(self):
        return {'type': 'ir.actions.act_window_close'}
