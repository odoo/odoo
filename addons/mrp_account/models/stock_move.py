# Part of Odoo. See LICENSE file for full copyright and licensing details.

<<<<<<< 9ab3f4e4e70f501e4d2acaf2ffab8531c667b9e2
from odoo import _, models
||||||| 995a7072cb3315fc03544b281b1ed5ca4e81e901
from collections import defaultdict

from odoo import models
=======
from collections import defaultdict

from odoo import _, Command, fields, models
>>>>>>> 27fa43467d14f6d4aa0bcfe5b135b3c5a429df18


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_value_data(self,
        forced_std_price=False,
        at_date=False,
        ignore_manual_update=False,
        add_computed_value_to_description=False):
        self.ensure_one()
        if self.production_id:
            valued_qty = self._get_valued_qty()
            return {
                'value': self._get_value_from_production(valued_qty),
                'quantity': valued_qty,
                'description': _('From Production Order %(reference)s', reference=self.production_id.name),
            }
        return super()._get_value_data(forced_std_price, at_date, ignore_manual_update, add_computed_value_to_description)

    def _get_value_from_production(self, quantity):
        # TODO: Maybe move _cal_price here
        self.ensure_one()
<<<<<<< 9ab3f4e4e70f501e4d2acaf2ffab8531c667b9e2
        return quantity * self.price_unit
||||||| 995a7072cb3315fc03544b281b1ed5ca4e81e901
        return self.location_id.usage == 'production' and self.location_dest_id._should_be_valued()

    def _is_production_consumed(self):
        self.ensure_one()
        return self.location_dest_id.usage == 'production' and self.location_id._should_be_valued()

    def _get_out_svl_vals(self, forced_quantity):
        unbuild_moves = self.filtered('unbuild_id')
        # 'real cost' of finished product moves @ build time
        price_unit_map = {
            move.id: (
                (move.unbuild_id.mo_id.move_finished_ids |
                move.unbuild_id.mo_id.move_raw_ids).stock_valuation_layer_ids.filtered(
                    lambda svl: svl.product_id == move.product_id
                )[0].unit_cost,
                move.company_id.currency_id.round,
            )
            for move in unbuild_moves.sudo()
            if move.product_id.cost_method != 'standard' and
            move.unbuild_id.mo_id.move_finished_ids.stock_valuation_layer_ids
        }
        svl_vals_list = super()._get_out_svl_vals(forced_quantity)
        if price_unit_map:
            for svl_vals in svl_vals_list:
                if (move_id := svl_vals['stock_move_id']) in price_unit_map:
                    unit_cost = price_unit_map[move_id][0]
                    svl_vals.update({
                        'unit_cost': unit_cost,
                        'value': price_unit_map[move_id][1](unit_cost * svl_vals['quantity']),
                    })
        return svl_vals_list

    def _create_out_svl(self, forced_quantity=None):
        product_unbuild_map = defaultdict(self.env['mrp.unbuild'].browse)
        for move in self:
            if move.unbuild_id:
                product_unbuild_map[move.product_id] |= move.unbuild_id
        return super(StockMove, self.with_context(product_unbuild_map=product_unbuild_map))._create_out_svl(forced_quantity)
=======
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
>>>>>>> 27fa43467d14f6d4aa0bcfe5b135b3c5a429df18

    def _get_all_related_sm(self, product):
        moves = super()._get_all_related_sm(product)
        return moves | self.filtered(
            lambda m:
            m.bom_line_id.bom_id.type == 'phantom' and
            m.bom_line_id.bom_id == moves.bom_line_id.bom_id
        )
