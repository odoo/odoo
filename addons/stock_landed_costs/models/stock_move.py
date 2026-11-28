from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_landed_cost(self):
        domain = [('move_id', 'in', self.ids), ('cost_id.state', '=', 'done')]
        # We have to use sudo to make sure the users with scoped access to landed costs won't
        # silently end up with the wrong values.
        landed_cost_group = self.env['stock.valuation.adjustment.lines'].sudo()._read_group(
            domain, ['move_id'], ['id:recordset'])
        return dict(landed_cost_group)

    def _get_value_from_std_price(self, quantity, std_price=False):
        res = super()._get_value_from_std_price(quantity, std_price)
        validating = self.env.context.get('landed_cost_in_progress')
        if validating and not std_price and self.product_id.cost_method in ('fifo', 'average'):
            # Keep the move's base cost: product and lot costs already absorbed its landed costs
            # and the other moves' values.
            valued_qty = self._get_valued_qty()
            if valued_qty:
                applied = sum(
                    lc.additional_landed_cost
                    for lc in self._get_landed_cost().get(self, [])
                    if lc.cost_id.id != validating
                )
                res['value'] = (self.value - applied) / valued_qty * quantity
        return res

    def _get_value_from_extra(self, quantity):
        self.ensure_one()
        accounting_data = super()._get_value_from_extra(quantity)
        # Add landed costs value
        lcs = self._get_landed_cost()
        lcs = lcs.get(self)
        if not lcs:
            return accounting_data
        lcs_desc = []
        # We had to sudo to get the correct values, but we should still hide the names of
        # the bills and the landed costs if the user isn't allowed to access those records.
        costs, bills = lcs.cost_id, lcs.cost_id.vendor_bill_id
        if not self.env.su:
            costs = costs.sudo(False)._filtered_access('read')
            bills = bills.sudo(False)._filtered_access('read')
        for lc in lcs:
            accounting_data["value"] += lc.additional_landed_cost
            landed_cost = lc.cost_id
            value = lc.additional_landed_cost
            vendor_bill = landed_cost.vendor_bill_id
            if landed_cost in costs and vendor_bill in bills:
                desc = self.env._("+ %(value)s from %(vendor_bill)s (Landed Cost: %(landed_cost)s)",
                    value=self.company_currency_id.format(value), vendor_bill=vendor_bill.display_name, landed_cost=landed_cost.display_name)
            elif landed_cost in costs:
                desc = self.env._("+ %(value)s (Landed Cost: %(landed_cost)s)",
                    value=self.company_currency_id.format(value), landed_cost=landed_cost.display_name)
            else:
                desc = self.env._("+ %(value)s (Landed Cost)",
                    value=self.company_currency_id.format(value))
            lcs_desc.append(desc)
        description = self.env._("Additional landed costs:\n%(landed_cost)s", landed_cost='\n'.join(lcs_desc))
        if not accounting_data['description']:
            accounting_data['description'] = description
        else:
            accounting_data['description'] += '\n' + description
        return accounting_data
