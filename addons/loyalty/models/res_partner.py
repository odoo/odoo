# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    loyalty_points = fields.Float(company_dependent=True, help='The loyalty points the user won as part of a Loyalty Program')

    @api.constrains('loyalty_points')
    def _check_loyalty_points(self):
        for record in self:
            if record.loyalty_points < 0:
                raise ValidationError(
                    _('Loyalty points cannot be negative')
                )
