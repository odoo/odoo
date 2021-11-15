# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.float_utils import float_is_zero


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    value = fields.Monetary('Value', compute='_compute_value', groups='stock.group_stock_manager')
    currency_id = fields.Many2one('res.currency', compute='_compute_value', groups='stock.group_stock_manager')
    accounting_date = fields.Date(
        'Accounting Date',
        help="Date at which the accounting entries will be created"
             " in case of automated inventory valuation."
             " If empty, the inventory date will be used.")

    @api.depends('company_id', 'location_id', 'owner_id', 'product_id', 'quantity')
    def _compute_value(self):
        """ For standard and AVCO valuation, compute the current accounting
        valuation of the quants by multiplying the quantity by
        the standard price. Instead for FIFO, use the quantity times the
        average cost (valuation layers are not manage by location so the
        average cost is the same for all location and the valuation field is
        a estimation more than a real value).
        """
        for quant in self:
            quant.currency_id = quant.company_id.currency_id
            # If the user didn't enter a location yet while enconding a quant.
            if not quant.location_id:
                quant.value = 0
                return

            if not quant.location_id._should_be_valued() or\
                    (quant.owner_id and quant.owner_id != quant.company_id.partner_id):
                quant.value = 0
                continue
            if quant.product_id.cost_method == 'fifo':
                quantity = quant.product_id.with_company(quant.company_id).quantity_svl
                if float_is_zero(quantity, precision_rounding=quant.product_id.uom_id.rounding):
                    quant.value = 0.0
                    continue
                average_cost = quant.product_id.with_company(quant.company_id).value_svl / quantity
                quant.value = quant.quantity * average_cost
            else:
                quant.value = quant.quantity * quant.product_id.with_company(quant.company_id).standard_price

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """ This override is done in order for the grouped list view to display the total value of
        the quants inside a location. This doesn't work out of the box because `value` is a computed
        field.
        """
        if 'value' not in fields:
            return super(StockQuant, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        res = super(StockQuant, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        for group in res:
            if group.get('__domain'):
                quants = self.search(group['__domain'])
                group['value'] = sum(quant.value for quant in quants)
        return res

    def _apply_inventory(self):
        acc_inventories = self.filtered(lambda quant: quant.accounting_date)
        for inventory in acc_inventories:
            super(StockQuant, self.with_context(force_period_date=inventory.accounting_date))._apply_inventory()
            inventory.write({'accounting_date': False})
        other_inventories = self - acc_inventories
        if other_inventories:
            super(StockQuant, other_inventories)._apply_inventory()

    @api.model
    def _get_inventory_fields_write(self):
        """ Returns a list of fields user can edit when editing a quant in `inventory_mode`."""
        res = super()._get_inventory_fields_write()
        res += ['accounting_date']
        return res
