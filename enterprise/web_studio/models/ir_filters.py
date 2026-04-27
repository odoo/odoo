# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrFilters(models.Model):
    _name = 'ir.filters'
    _inherit = ['studio.mixin', 'ir.filters']
