# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models

class ResUsers(models.Model):
    _inherit = 'res.users'
    sale_team_id = fields.Many2one('crm.team', string='Sales Team')
