# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        """ Trigger automatic subscription based on user groups """
        users = super().create(vals_list)
        for user in users:
            self.env['slide.channel'].sudo().search([
                ('enroll_group_ids', 'in', user.all_group_ids.ids)
            ])._action_add_members(user.partner_id)
        return users

    def write(self, vals):
        """ Trigger automatic subscription based on updated user groups """
        res = super().write(vals)
        sanitized_vals = self._remove_reified_groups(vals)
        if sanitized_vals.get('group_ids'):
            added_group_ids = [command[1] for command in sanitized_vals['group_ids'] if command[0] == 4]
            added_group_ids += [id for command in sanitized_vals['group_ids'] if command[0] == 6 for id in command[2]]
            self.env['slide.channel'].sudo().search([('enroll_group_ids', 'in', added_group_ids)])._action_add_members(self.mapped('partner_id'))
        return res

    def get_gamification_redirection_data(self):
        res = super().get_gamification_redirection_data()
        res.append({
            'url': '/slides',
            'label': _('See our eLearning')
        })
        return res
