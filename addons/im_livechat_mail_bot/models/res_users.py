# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class Users(models.Model):
    _inherit = 'res.users'
    odoobot_state = fields.Selection(
        selection_add=[
            ('onboarding_canned', 'Onboarding canned'),
        ])
