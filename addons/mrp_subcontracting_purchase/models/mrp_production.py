
from odoo import Command, fields, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    subcontract_extra_move_id = fields.Many2one(
        'account.move', string="Subcontracting Cost Entry", copy=False,
        help="Journal entry neutralising the subcontractor bill's stock valuation, so the "
             "finished move keeps the full cost while the bill is not counted twice.")

    def _post_inventory(self, cancel_backorder=False):
        res = super()._post_inventory(cancel_backorder=cancel_backorder)
        self.filtered(lambda mo: mo.state == 'done')._post_subcontract_extra_cost()
        return res

    def _post_subcontract_extra_cost(self):
        """ The finished move's ``value`` (and hence the stock valuation entry) already
        includes the subcontractor's charge (``extra_cost``). The subcontractor bill books
        that same charge on the stock valuation account too, so post a balanced entry that
        moves the billed part back out of stock valuation and onto the production account,
        leaving stock valuation with the finished good's full value counted once. """
        for production in self:
            if production.subcontract_extra_move_id:
                continue
            if production.product_id.cost_method == 'standard':
                continue
            production_location = production.product_id.with_company(production.company_id).property_stock_production
            if production.product_id.valuation != 'real_time' or not production_location.valuation_account_id:
                continue
            product_accounts = production.product_id.product_tmpl_id.get_product_accounts()
            stock_valuation_account = product_accounts['stock_valuation']
            if not stock_valuation_account:
                continue

            finished_moves = production.move_finished_ids.filtered(
                lambda m: m.product_id == production.product_id and m.state == 'done')
            amount = 0
            for finished_move in finished_moves:
                receipt = finished_move.move_dest_ids.filtered(
                    lambda m: m.state == 'done' and m.is_subcontract and m.purchase_line_id
                ).sorted('create_date', reverse=True)[:1]
                if not receipt:
                    continue
                qty = finished_move.uom_id._compute_quantity(finished_move.quantity, finished_move.product_id.uom_id)
                amount += receipt._get_value_from_account_move(qty)['value']
            amount = production.company_id.currency_id.round(amount)
            if production.company_id.currency_id.is_zero(amount):
                continue

            desc = production.env._("%(name)s - Subcontracting", name=production.name)
            account_move = self.env['account.move'].sudo().create({
                'journal_id': product_accounts['stock_journal'].id,
                'date': fields.Date.context_today(production),
                'ref': desc,
                'move_type': 'entry',
                'line_ids': [
                    Command.create({
                        'name': desc,
                        'product_id': production.product_id.id,
                        'account_id': production_location.valuation_account_id.id,
                        'balance': amount,
                    }),
                    Command.create({
                        'name': desc,
                        'product_id': production.product_id.id,
                        'account_id': stock_valuation_account.id,
                        'balance': -amount,
                    }),
                ],
            })
            account_move._post()
            production.subcontract_extra_move_id = account_move.id
