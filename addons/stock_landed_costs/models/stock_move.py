from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_landed_cost(self, at_date=None):
        domain = [('move_id', 'in', self.ids), ('cost_id.state', '=', 'done')]
        if at_date:
            domain.append(('cost_id.date', '<=', at_date))
        landed_cost_group = self.env['stock.valuation.adjustment.lines']._read_group(domain, ['move_id'], ['id:recordset'])
        return dict(landed_cost_group)

    def _with_cost_before_landed_costs(self):
        """ Moves valued at the product cost (e.g. receipts without purchase order) would be
        revalued at the current product cost, which already includes the landed costs applied
        on them. Keep the cost they were valued at instead, without their landed costs. """
        landed_costs = self._get_landed_cost()
        unit_costs = {}
        for move in self.filtered(lambda m: m.state == 'done' and m.is_in):
            valued_qty = move._get_valued_qty()
            if move.product_id.uom_id.is_zero(valued_qty):
                continue
            previous_landed_cost = sum(landed_costs[move].mapped('additional_landed_cost')) if move in landed_costs else 0
            unit_costs[move.id] = (move.value - previous_landed_cost) / valued_qty
        return self.with_context(cost_before_landed_costs=unit_costs)

    def _get_value_from_std_price(self, quantity, std_price=False, at_date=None):
        value_data = super()._get_value_from_std_price(quantity, std_price=std_price, at_date=at_date)
        unit_cost = self.env.context.get('cost_before_landed_costs', {}).get(self.id)
        # Only when the whole move is valued at the product cost, otherwise its value also
        # contains other sources (e.g. a purchase order)
        if unit_cost is not None and not std_price and not at_date \
                and self.product_id.uom_id.compare(quantity, self._get_valued_qty()) == 0:
            value_data['value'] = unit_cost * quantity
        return value_data

    def _get_value_from_extra(self, quantity, at_date=None):
        self.ensure_one()
        accounting_data = super()._get_value_from_extra(quantity, at_date=at_date)
        # Add landed costs value
        lcs = self._get_landed_cost(at_date=at_date)
        lcs = lcs.get(self)
        if not lcs:
            return accounting_data
        lcs_desc = []
        for lc in lcs:
            accounting_data["value"] += lc.additional_landed_cost
            landed_cost = lc.cost_id
            value = lc.additional_landed_cost
            vendor_bill = landed_cost.vendor_bill_id
            if vendor_bill:
                desc = self.env._("+ %(value)s from %(vendor_bill)s (Landed Cost: %(landed_cost)s)",
                    value=self.company_currency_id.format(value), vendor_bill=vendor_bill.display_name, landed_cost=landed_cost.display_name)
            else:
                desc = self.env._("+ %(value)s (Landed Cost: %(landed_cost)s)",
                    value=self.company_currency_id.format(value), landed_cost=landed_cost.display_name)
            lcs_desc.append(desc)
        description = self.env._("Additional landed costs:\n%(landed_cost)s", landed_cost='\n'.join(lcs_desc))
        if not accounting_data['description']:
            accounting_data['description'] = description
        else:
            accounting_data['description'] += '\n' + description
        return accounting_data
