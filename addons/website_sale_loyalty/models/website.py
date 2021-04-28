# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Website(models.Model):
    _inherit = 'website'

    def _default_loyalty_program(self):
        return self.env['loyalty.program'].search([], limit=1)

    has_loyalty = fields.Boolean("Has Loyalty Program", help="Enables a loyalty program for this website", default=False)
    loyalty_id = fields.Many2one('loyalty.program', string='Loyalty Program', help='The loyalty program used by this website', default=_default_loyalty_program)

    @api.onchange('has_loyalty')
    def _onchange_has_loyalty(self):
        self.loyalty_id = self.has_loyalty and self._default_loyalty_program()
