from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_landed_cost(self, at_date=None):
        domain = [('move_id', 'in', self.ids), ('cost_id.state', '=', 'done')]
        if at_date:
            domain.append(('cost_id.date', '<=', at_date))
        landed_cost_group = self.env['stock.valuation.adjustment.lines']._read_group(domain, ['move_id'], ['id:recordset'])
        return dict(landed_cost_group)

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
        description = self.env._("including landed costs:\n%(landed_cost)s", landed_cost='\n'.join(lcs_desc))
        if not accounting_data['description']:
            accounting_data['description'] = description
        else:
            accounting_data['description'] += '\n' + description
        return accounting_data
