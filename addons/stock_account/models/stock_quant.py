# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
from odoo import api, fields, models, _
from odoo.tools.float_utils import float_is_zero
from odoo.tools.misc import groupby


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    value = fields.Monetary('Value', compute='_compute_value', groups='stock.group_stock_manager')
    currency_id = fields.Many2one('res.currency', compute='_compute_value', groups='stock.group_stock_manager')
    accounting_date = fields.Date(
        'Accounting Date',
        help="Date at which the accounting entries will be created"
             " in case of automated inventory valuation."
             " If empty, the inventory date will be used.")
    cost_method = fields.Selection(related="product_categ_id.property_cost_method")

    @api.model
    def _should_exclude_for_valuation(self):
        """
        Determines if a quant should be excluded from valuation based on its ownership.
        :return: True if the quant should be excluded from valuation, False otherwise.
        """
        self.ensure_one()
        return self.owner_id and self.owner_id != self.company_id.partner_id

    @api.depends('company_id', 'location_id', 'owner_id', 'product_id', 'quantity')
    def _compute_value(self):
        """ (Product.value_svl / Product.quantity_svl) * quant.quantity, i.e. average unit cost * on hand qty
        """
        self.fetch(['company_id', 'location_id', 'owner_id', 'product_id', 'quantity', 'lot_id'])
        self.value = 0
        for quant in self:
            quant.currency_id = quant.company_id.currency_id
            if not quant.location_id or not quant.product_id or\
                    not quant.location_id._should_be_valued() or\
                    quant._should_exclude_for_valuation() or\
                    float_is_zero(quant.quantity, precision_rounding=quant.product_id.uom_id.rounding):
                continue
            if quant.product_id.lot_valuated:
                quantity = quant.lot_id.with_company(quant.company_id).quantity_svl
                value_svl = quant.lot_id.with_company(quant.company_id).value_svl
            else:
                quantity = quant.product_id.with_company(quant.company_id).quantity_svl
                value_svl = quant.product_id.with_company(quant.company_id).value_svl
            if float_is_zero(quantity, precision_rounding=quant.product_id.uom_id.rounding):
                continue
            quant.value = quant.quantity * value_svl / quantity

    def _read_group_select(self, aggregate_spec, query):
        # flag value as aggregatable, and manually sum the values from the
        # records in the group
        if aggregate_spec == 'value:sum':
            return super()._read_group_select('id:recordset', query)
        return super()._read_group_select(aggregate_spec, query)

    def _read_group_postprocess_aggregate(self, aggregate_spec, raw_values):
        if aggregate_spec == 'value:sum':
            column = super()._read_group_postprocess_aggregate('id:recordset', raw_values)
            return (sum(records.mapped('value')) for records in column)
        return super()._read_group_postprocess_aggregate(aggregate_spec, raw_values)

    def _apply_inventory(self):
        for accounting_date, inventory_ids in groupby(self, key=lambda q: q.accounting_date):
            inventories = self.env['stock.quant'].concat(*inventory_ids)
            if accounting_date:
                super(StockQuant, inventories.with_context(force_period_date=accounting_date))._apply_inventory()
                inventories.accounting_date = False
            else:
                super(StockQuant, inventories)._apply_inventory()

    def _get_inventory_move_values(self, qty, location_id, location_dest_id, package_id=False, package_dest_id=False):
        res_move = super()._get_inventory_move_values(qty, location_id, location_dest_id, package_id, package_dest_id)
        if not self.env.context.get('inventory_name'):
            force_period_date = self.env.context.get('force_period_date', False)
            if force_period_date:
                res_move['name'] += _(' [Accounted on %s]', force_period_date)
        return res_move

    @api.model
    def _get_inventory_fields_write(self):
        """ Returns a list of fields user can edit when editing a quant in `inventory_mode`."""
        res = super()._get_inventory_fields_write()
        res += ['accounting_date']
        return res
