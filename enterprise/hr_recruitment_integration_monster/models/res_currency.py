# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    monster_id = fields.Integer(string="Monster ID")
