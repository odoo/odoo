# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_value_data(self,
        forced_std_price=False,
        at_date=False,
        ignore_manual_update=False):
        self.ensure_one()
        if self.production_id:
            valued_qty = self._get_valued_qty()
            return {
                'value': self._get_value_from_production(valued_qty),
                'quantity': valued_qty,
                'description': _('From Production Order %(reference)s', reference=self.production_id.name),
            }
        return super()._get_value_data(forced_std_price, at_date, ignore_manual_update)

    def _get_value_from_production(self, quantity):
        # TODO: Maybe move _cal_price here
        self.ensure_one()
<<<<<<< 255077278aba239de50744f597b0a8876dcea2ca
        return quantity * self.price_unit

||||||| 3560c9cd694f6403d4c83ab2417e2fee3eccb0b5
        return self.location_id.usage == 'production' and self.location_dest_id._should_be_valued()

    def _is_production_consumed(self):
        self.ensure_one()
        return self.location_dest_id.usage == 'production' and self.location_id._should_be_valued()

    def _create_out_svl(self, forced_quantity=None):
        svls = super()._create_out_svl(forced_quantity)
        unbuild_svls = svls.filtered('stock_move_id.unbuild_id')
        unbuild_cost_correction_move_list = list()
        for svl in unbuild_svls:
            build_time_unit_cost = svl.stock_move_id.unbuild_id.mo_id.move_finished_ids.filtered(
                lambda m: m.product_id == svl.product_id
            ).stock_valuation_layer_ids.unit_cost
            unbuild_difference = svl.unit_cost - build_time_unit_cost
            if svl.product_id.valuation == 'real_time' and not svl.currency_id.is_zero(unbuild_difference):
                product_accounts = svl.product_id.product_tmpl_id.get_product_accounts()
                valuation_account, production_account = (
                    product_accounts['stock_valuation'],
                    product_accounts['production'],
                )
                desc = _('%s - Unbuild Cost Difference', svl.stock_move_id.unbuild_id.name)
                unbuild_cost_correction_move_list.append({
                    'journal_id': product_accounts['stock_journal'].id,
                    'date': fields.Date.context_today(self),
                    'ref': desc,
                    'move_type': 'entry',
                    'line_ids': [Command.create({
                        'name': desc,
                        'ref': desc,
                        'account_id': account.id,
                        'balance': balance,
                        'product_id': svl.product_id.id,
                    }) for account, balance in (
                        (valuation_account, unbuild_difference),
                        (production_account, -unbuild_difference),
                    )],
                })
        if unbuild_cost_correction_move_list:
            unbuild_cost_correction_moves = self.env['account.move'].sudo().create(unbuild_cost_correction_move_list)
            unbuild_cost_correction_moves._post()
        return svls

=======
        return self.location_id.usage == 'production' and self.location_dest_id._should_be_valued()

    def _is_production_consumed(self):
        self.ensure_one()
        return self.location_dest_id.usage == 'production' and self.location_id._should_be_valued()

>>>>>>> a02b032c4e0936002255582423f68cdcd42bd62f
    def _get_all_related_sm(self, product):
        moves = super()._get_all_related_sm(product)
        return moves | self.filtered(
            lambda m:
            m.bom_line_id.bom_id.type == 'phantom' and
            m.bom_line_id.bom_id == moves.bom_line_id.bom_id
        )
