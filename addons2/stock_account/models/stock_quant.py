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
        self.fetch(['company_id', 'location_id', 'owner_id', 'product_id', 'quantity'])
        for quant in self:
            quant.currency_id = quant.company_id.currency_id
            if not quant.location_id or not quant.product_id or\
                    not quant.location_id._should_be_valued() or\
                    quant._should_exclude_for_valuation() or\
                    float_is_zero(quant.quantity, precision_rounding=quant.product_id.uom_id.rounding):
                quant.value = 0
                continue
            quantity = quant.product_id.with_company(quant.company_id).quantity_svl
            if float_is_zero(quantity, precision_rounding=quant.product_id.uom_id.rounding):
                quant.value = 0.0
                continue
            quant.value = quant.quantity * quant.product_id.with_company(quant.company_id).value_svl / quantity

    @api.model
    def _read_group(self, domain, groupby=(), aggregates=(), having=(), offset=0, limit=None, order=None):
        """ This override is done in order for the grouped list view to display the total value of
        the quants inside a location. This doesn't work out of the box because `value` is a computed
        field.
        """
        SPECIAL = {'value:sum'}
        if SPECIAL.isdisjoint(aggregates):
            return super()._read_group(domain, groupby, aggregates, having, offset, limit, order)

        base_aggregates = [*(agg for agg in aggregates if agg not in SPECIAL), 'id:recordset']
        base_result = super()._read_group(domain, groupby, base_aggregates, having, offset, limit, order)

        # base_result = [(a1, b1, records), (a2, b2, records), ...]
        result = []
        for *other, records in base_result:
            for index, spec in enumerate(itertools.chain(groupby, aggregates)):
                if spec in SPECIAL:
                    field_name = spec.split(':')[0]
                    other.insert(index, sum(records.mapped(field_name)))
            result.append(tuple(other))

        return result

    @api.model
    def read_group(self, domain, fields, *args, **kwargs):
        if 'value' in fields:
            fields = ['value:sum' if f == 'value' else f for f in fields]
        return super().read_group(domain, fields, *args, **kwargs)

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
