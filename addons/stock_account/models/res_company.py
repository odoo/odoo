# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Company(models.Model):
    _inherit = "res.company"

    inventory_revaluation_distribution_method = fields.Selection([("quantity", "Proportionate to quantity"), ("value", "Proportionate to value")],
                                                       "Inventory Revaluation Distribution Method",
                                                       help="Determines the method to distribute revaluations over existing values. It can be either proportionate to quantity (default) or proportionate to value.",
                                                       required=True,
                                                       default='quantity')
