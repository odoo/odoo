# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    expiration_date = fields.Datetime(related='lot_id.expiration_date', store=True, readonly=False)
    removal_date = fields.Datetime(related='lot_id.removal_date', store=True, readonly=False)
    use_expiration_date = fields.Boolean(related='product_id.use_expiration_date', readonly=True)

    @api.model
    def _get_inventory_fields_create(self):
        """ Returns a list of fields user can edit when he want to create a quant in `inventory_mode`.
        """
        res = super()._get_inventory_fields_create()
        res += ['expiration_date', 'removal_date']
        return res

    @api.model
    def _get_inventory_fields_write(self):
        """ Returns a list of fields user can edit when he want to edit a quant in `inventory_mode`.
        """
        res = super()._get_inventory_fields_write()
        res += ['expiration_date', 'removal_date']
        return res

    @api.model
    def _get_removal_strategy_domain_order(self, domain, removal_strategy, qty):
        if removal_strategy == 'fefo':
            return domain, 'removal_date, in_date, id'
        return super(StockQuant, self)._get_removal_strategy_domain_order(domain, removal_strategy, qty)
