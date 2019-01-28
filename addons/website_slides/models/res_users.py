# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Users(models.Model):
    _inherit = 'res.users'

    def get_gamification_redirection_data(self):
        res = super(Users, self).get_gamification_redirection_data()
        res.append({
            'url': '/slides',
            'label': 'See our eLearning'
        })
        return res
