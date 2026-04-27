# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class KnowledgeInvite(models.TransientModel):
    _name = 'knowledge.invite'
    _description = 'Knowledge Invite Wizard'

    article_id = fields.Many2one('knowledge.article', required=True, ondelete="cascade")
    have_share_partners = fields.Boolean(compute='_compute_have_share_partners')
    partner_ids = fields.Many2many('res.partner', string='Recipients', required=True)
    permission = fields.Selection([
        ('write', 'Can edit'),
        ('read', 'Can read'),
        ('none', 'No access')
    ], required=True, default='write')
    message = fields.Html(string="Message")

    def action_invite_members(self):
        self.article_id.invite_members(self.partner_ids, self.permission, self.message)

    @api.depends('partner_ids')
    def _compute_have_share_partners(self):
        for wizard in self:
            wizard.have_share_partners = any(partner_id.partner_share for partner_id in self.partner_ids)
