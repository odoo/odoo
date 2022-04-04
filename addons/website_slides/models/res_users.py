# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class Users(models.Model):
    _inherit = 'res.users'

    @api.model
    def create(self, values):
        """ Trigger automatic subscription based on user groups """
        user = super(Users, self).create(values)
        self.env['slide.channel'].sudo().search([('enroll_group_ids', 'in', user.groups_id.ids)])._action_add_members(user.partner_id)
        return user

    def write(self, vals):
        """ Trigger automatic subscription based on updated user groups """
        res = super(Users, self).write(vals)
        if vals.get('groups_id'):
            added_group_ids = [command[1] for command in vals['groups_id'] if command[0] == 4]
            added_group_ids += [id for command in vals['groups_id'] if command[0] == 6 for id in command[2]]
            self.env['slide.channel'].sudo().search([('enroll_group_ids', 'in', added_group_ids)])._action_add_members(self.mapped('partner_id'))
        return res

    def get_gamification_redirection_data(self):
        res = super(Users, self).get_gamification_redirection_data()
        res.append({
            'url': '/slides',
            'label': _('See our eLearning')
        })
        return res
