# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class ResPartnerIndustry(models.Model):
    _inherit = "res.partner.industry"

    _populate_sizes = {
        'small': 15,
        'medium': 60,
        'large': 300,
    }

    def _populate_factories(self):
        return [
            ('active', populate.cartesian([False, True], [0.1, 0.9])),
            ('name', populate.cartesian(
                [False, 'Industry name', 'Industry name {counter}'],
                [0.08, 0.01, 0.9])),
            ('full_name', populate.iterate([False, 'Industry full name %s']))
        ]
