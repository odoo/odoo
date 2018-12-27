# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class LunchSupplier(models.Model):
    _inherit = 'lunch.supplier'

    available_location_ids = fields.Many2many('res.partner', string='This Supplier is available at')
