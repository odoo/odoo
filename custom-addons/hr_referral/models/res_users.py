# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    hr_referral_level_id = fields.Many2one('hr.referral.level', groups="hr.group_hr_user")
    hr_referral_onboarding_page = fields.Boolean(groups="hr.group_hr_user")
    referral_point_ids = fields.One2many('hr.referral.points', 'ref_user_id')
    utm_source_id = fields.Many2one('utm.source', 'Source', ondelete="restrict", groups="hr.group_hr_user")

    @api.model
    def action_complete_onboarding(self, complete):
        if not self.env.user:
            return
        self.env.user.hr_referral_onboarding_page = bool(complete)

    def _clean_responsibles(self):
        reward_responsible_group = self.env.ref('hr_referral.group_hr_referral_reward_responsible_user', raise_if_not_found=False)
        if not self or not reward_responsible_group:
            return
        res = self.env['hr.referral.reward']._read_group(
            [('gift_manager_id', 'in', self.ids)],
            ['gift_manager_id'])
        responsibles_to_remove_ids = set(self.ids) - {gift_manager.id for [gift_manager] in res}
        reward_responsible_group.sudo().write({
            'users': [(3, responsible_id) for responsible_id in responsibles_to_remove_ids]})
