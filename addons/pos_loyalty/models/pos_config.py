# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    loyalty_id = fields.Many2one('loyalty.program', string='Loyalty Program', help='The loyalty program used by this point_of_sale')
