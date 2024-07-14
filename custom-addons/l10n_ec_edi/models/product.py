# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_ec_withhold_tax_id = fields.Many2one(
        comodel_name='account.tax',
        company_dependent=True,
        string="Profit Withhold",
        domain=[('tax_group_id.l10n_ec_type', '=', 'withhold_income_purchase')],
        help="Ecuador: Default profit withholding tax when the product is purchased.",
    )
