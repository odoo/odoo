# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    property_stock_account_production_cost_id = fields.Many2one(
        'account.account', "Production Account",
        check_company=True,
        domain="[('deprecated', '=', False)]",
        compute='_compute_property_stock_account',
        inverse='_set_property_stock_account_production_cost_id')

    @api.model
    def _get_account_stock_properties_names(self):
        return super()._get_account_stock_properties_names() + [
            'property_stock_account_production_cost_id',
        ]

    def _set_property_stock_account_production_cost_id(self):
        for record in self:
            record._set_property('property_stock_account_production_cost_id')
