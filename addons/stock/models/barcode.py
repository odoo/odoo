# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _


class BarcodeRule(models.Model):
    _inherit = 'barcode.rule'

    type = fields.Selection(selection_add=[
            ('weight', _('Weighted Product')),
            ('location', _('Location')),
            ('lot', _('Lot')),
            ('package', _('Package'))
        ])
