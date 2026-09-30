# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint

from odoo import api, fields, models


class HrHeadcountWorkingRate(models.Model):
    _name = 'hr.headcount.working.rate'
    _description = 'Working Rate'

    rate = fields.Float(string='Rate')
    color = fields.Integer(string='Color', default=lambda self: randint(1, 11))

    @api.depends('rate')
    def _compute_display_name(self):
        for working_rate in self:
            working_rate.display_name = self.env._('%(rate)s Hours/week', rate=working_rate.rate)
