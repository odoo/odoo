# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class BarcodeRule(models.Model):
    _inherit = 'barcode.rule'

    def _get_type_selection(self):
        types = set(super(BarcodeRule, self)._get_type_selection())
        types.update([
            ('weight', _('Weighted Product')),
            ('location', _('Location')),
            ('lot', _('Lot')),
            ('package', _('Package'))
        ])
        return list(types)
