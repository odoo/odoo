# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.osv import expression
from odoo.tools import float_compare, float_is_zero, float_round, groupby


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    def _get_product_accounts(self):
        accounts = super()._get_product_accounts()
        accounts.update({
            'production': self.categ_id.property_stock_account_production_cost_id,
        })
        return accounts

    def action_bom_cost(self):
        templates = self.filtered(lambda t: t.product_variant_count == 1 and t.bom_count > 0)
        if templates:
            return templates.mapped('product_variant_id').action_bom_cost()

    def button_bom_cost(self):
        templates = self.filtered(lambda t: t.product_variant_count == 1 and t.bom_count > 0)
        if templates:
            return templates.mapped('product_variant_id').button_bom_cost()


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    def _post_fifo_vacuum(self, vacuum_svls):
        super()._post_fifo_vacuum(vacuum_svls)
        mo_vacuum_svls = vacuum_svls.filtered(
            lambda s: s.stock_move_id.raw_material_production_id.state == 'done'
        )
        if not mo_vacuum_svls:
            return
        new_svl_vals = []
        for component_vacuum_svl in mo_vacuum_svls:
            mo = component_vacuum_svl.stock_move_id.raw_material_production_id
            finished_moves = mo.move_finished_ids.filtered(
                lambda m: m.state == 'done' and m.product_id == mo.product_id
            )
            if not finished_moves:
                continue
            correction = -component_vacuum_svl.value
            if component_vacuum_svl.currency_id.is_zero(correction):
                continue
            total_qty = sum(finished_moves.mapped('quantity'))
            for finished_move in finished_moves:
                move_correction = correction * finished_move.quantity / total_qty if total_qty else correction
                move_correction = component_vacuum_svl.currency_id.round(move_correction)
                if component_vacuum_svl.currency_id.is_zero(move_correction):
                    continue
                base_svl = finished_move.stock_valuation_layer_ids.filtered(
                    lambda s: not s.stock_valuation_layer_id
                    and float_compare(s.quantity, 0, precision_rounding=s.product_id.uom_id.rounding) > 0
                )[:1]
                if base_svl:
                    move_qty = finished_move.product_uom._compute_quantity(
                        finished_move.quantity, finished_move.product_id.uom_id)
                    remaining_qty = sum(finished_move.stock_valuation_layer_ids.mapped('remaining_qty'))
                    if not float_is_zero(remaining_qty, precision_rounding=finished_move.product_id.uom_id.rounding) and not float_is_zero(move_qty, precision_rounding=finished_move.product_uom.rounding):
                        base_svl.sudo().remaining_value += move_correction * remaining_qty / move_qty
                new_svl_vals.append({
                    'product_id': finished_move.product_id.id,
                    'value': move_correction,
                    'unit_cost': 0,
                    'quantity': 0,
                    'remaining_qty': 0,
                    'stock_move_id': finished_move.id,
                    'company_id': finished_move.company_id.id,
                    'description': component_vacuum_svl.description,
                    'stock_valuation_layer_id': base_svl.id if base_svl else False,
                })
        if new_svl_vals:
            finished_vacuum_svls = self.env['stock.valuation.layer'].sudo().create(new_svl_vals)
            finished_vacuum_svls._validate_accounting_entries()

    def button_bom_cost(self):
        self.ensure_one()
        self._set_price_from_bom()

    def action_bom_cost(self):
        boms_to_recompute = self.env['mrp.bom'].search(['|', ('product_id', 'in', self.ids), '&', ('product_id', '=', False), ('product_tmpl_id', 'in', self.mapped('product_tmpl_id').ids)])
        for product in self:
            product._set_price_from_bom(boms_to_recompute)

    def _set_price_from_bom(self, boms_to_recompute=False):
        self.ensure_one()
        bom = self.env['mrp.bom']._bom_find(self)[self]
        if bom:
            self.standard_price = self._compute_bom_price(bom, boms_to_recompute=boms_to_recompute)
        else:
            bom = self.env['mrp.bom'].search([('byproduct_ids.product_id', '=', self.id)], order='sequence, product_id, id', limit=1)
            if bom:
                price = self._compute_bom_price(bom, boms_to_recompute=boms_to_recompute, byproduct_bom=True)
                if price:
                    self.standard_price = price

    def _compute_average_price(self, qty_invoiced, qty_to_invoice, stock_moves, is_returned=False):
        self.ensure_one()
        if stock_moves.product_id == self:
            return super()._compute_average_price(qty_invoiced, qty_to_invoice, stock_moves, is_returned=is_returned)
        bom = self.env['mrp.bom']._bom_find(self, company_id=stock_moves.company_id.id, bom_type='phantom')[self]
        if not bom:
            return super()._compute_average_price(qty_invoiced, qty_to_invoice, stock_moves, is_returned=is_returned)
        value = 0
        dummy, bom_lines = bom.explode(self, 1)
        bom_lines = {line: data for line, data in bom_lines}
        for bom_line, moves_list in groupby(stock_moves.filtered(lambda sm: sm.state != 'cancel'), lambda sm: sm.bom_line_id):
            if bom_line not in bom_lines:
                for move in moves_list:
                    component_quantity = next(
                        (bml.product_qty for bml in move.product_id.bom_line_ids if bml in bom_lines),
                        1
                    )
                    value += component_quantity * move.product_id._compute_average_price(qty_invoiced * move.product_qty, qty_to_invoice * move.product_qty, move, is_returned=is_returned)
                continue
            line_qty = bom_line.product_uom_id._compute_quantity(bom_lines[bom_line]['qty'], bom_line.product_id.uom_id)
            moves = self.env['stock.move'].concat(*moves_list)
            value += line_qty * bom_line.product_id._compute_average_price(qty_invoiced * line_qty, qty_to_invoice * line_qty, moves, is_returned=is_returned)
        return bom.product_uom_id._compute_price(value / bom.product_qty, self.uom_id)

    def _compute_bom_price(self, bom, boms_to_recompute=False, byproduct_bom=False):
        self.ensure_one()
        if not bom:
            return 0
        if not boms_to_recompute:
            boms_to_recompute = []
        total = 0
        for opt in bom.operation_ids:
            if opt._skip_operation_line(self):
                continue

            duration_expected = (
                opt.workcenter_id._get_expected_duration(self) +
                opt.time_cycle * 100 / opt.workcenter_id.time_efficiency)
            total += (duration_expected / 60) * opt._total_cost_per_hour()

        for line in bom.bom_line_ids:
            if line._skip_bom_line(self):
                continue

            # Compute recursive if line has `child_line_ids`
            if line.child_bom_id and line.child_bom_id in boms_to_recompute:
                child_total = line.product_id._compute_bom_price(line.child_bom_id, boms_to_recompute=boms_to_recompute)
                total += line.product_id.uom_id._compute_price(child_total, line.product_uom_id) * line.product_qty
            else:
                total += line.product_id.uom_id._compute_price(line.product_id.standard_price, line.product_uom_id) * line.product_qty
        if byproduct_bom:
            byproduct_lines = bom.byproduct_ids.filtered(lambda b: b.product_id == self and b.cost_share != 0)
            product_uom_qty = 0
            for line in byproduct_lines:
                product_uom_qty += line.product_uom_id._compute_quantity(line.product_qty, self.uom_id, round=False)
            byproduct_cost_share = sum(byproduct_lines.mapped('cost_share'))
            if byproduct_cost_share and product_uom_qty:
                return total * byproduct_cost_share / 100 / product_uom_qty
        else:
            byproduct_cost_share = sum(bom.byproduct_ids.mapped('cost_share'))
            if byproduct_cost_share:
                total *= float_round(1 - byproduct_cost_share / 100, precision_rounding=0.0001)
            return bom.product_uom_id._compute_price(total / bom.product_qty, self.uom_id)


class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_stock_account_production_cost_id = fields.Many2one(
        'account.account', 'Production Account', company_dependent=True,
        domain="[('deprecated', '=', False)]", check_company=True,
        help="""This account will be used as a valuation counterpart for both components and final products for manufacturing orders.
                If there are any workcenter/employee costs, this value will remain on the account once the production is completed.""")

    def write(self, vals):
        return super(ProductCategory, self.with_context(product_category_mrp_account_write=True)).write(vals)

    def _get_stock_account_property_field_names(self):
        mrp_value = ['property_stock_account_production_cost_id'] if self.property_stock_account_production_cost_id or not self.env.context.get('product_category_mrp_account_write') else []
        return super()._get_stock_account_property_field_names() + mrp_value
