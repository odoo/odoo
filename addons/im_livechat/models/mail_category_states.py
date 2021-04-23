# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class CategoryStates(models.Model):

    _inherit = 'mail.category.states'

    is_category_livechat_open = fields.Boolean("Is category livechat open", default=True)

    @api.model
    def _states_info(self, states):
        """ Override to add livechat category
        """
        info = super()._states_info(states)
        info['is_category_livechat_open'] = states.is_category_livechat_open
        return info

    @api.model
    def set_category_states(self, category, is_open):
        """ Override to add livechat category
        """
        states = self._get_states()
        if category == 'livechat':
            states.write({'is_category_livechat_open': is_open})
        return super().set_category_states(category, is_open)
