# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CategoryStates(models.Model):

    _name = 'mail.category.states'
    _description = 'States of categories'

    is_category_channel_open = fields.Boolean(string='Is category channel open', default=True)
    is_category_chat_open = fields.Boolean(string='Is category chat open', default=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, required=True)

    @api.model
    def _get_states(self):
        states = self.env['mail.category.states'].search([
            ('user_id', '=', self.env.user.id)
        ], limit=1)
        if not states:
            states = self.create({})
        return states

    @api.model
    def _states_info(self, states):
        return {
            "is_category_channel_open": states.is_category_channel_open,
            "is_category_chat_open": states.is_category_chat_open,
        }

    @api.model
    def get_category_states(self):
        states = self._get_states()
        return self._states_info(states)

    @api.model
    def set_category_states(self, category, is_open):
        states = self._get_states()
        if category == 'chat':
            states.write({'is_category_chat_open': is_open})
        elif category == 'channel':
            states.write({'is_category_channel_open': is_open})
        notif = self._states_info(states)
        notif['type'] = 'category_states'
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', states.user_id.partner_id.id), notif)

