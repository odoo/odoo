# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import gamification, hr


class ResUsers(gamification.ResUsers, hr.ResUsers):

    goal_ids = fields.One2many('gamification.goal', 'user_id')
    badge_ids = fields.One2many('gamification.badge.user', 'user_id')
