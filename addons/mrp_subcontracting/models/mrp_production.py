# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from collections import defaultdict
from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.tools.float_utils import float_compare, float_is_zero


class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    _rec_names_search = ['name', 'incoming_picking.name']

    move_line_raw_ids = fields.One2many(
        'stock.move.line', string="Detail Component", readonly=False,
        inverse='_inverse_move_line_raw_ids', compute='_compute_move_line_raw_ids'
    )
    subcontracting_has_been_recorded = fields.Boolean("Has been recorded?", copy=False)  # TODO: remove in master
    subcontractor_id = fields.Many2one('res.partner', string="Subcontractor", help="Used to restrict access to the portal user through Record Rules")
    bom_product_ids = fields.Many2many('product.product', compute="_compute_bom_product_ids", help="List of Products used in the BoM, used to filter the list of products in the subcontracting portal view")

    incoming_picking = fields.Many2one(related='move_finished_ids.move_dest_ids.picking_id')

    @api.depends('move_raw_ids.move_line_ids')
    def _compute_move_line_raw_ids(self):
        for production in self:
            production.move_line_raw_ids = production.move_raw_ids.move_line_ids

    def _compute_bom_product_ids(self):
        for production in self:
            production.bom_product_ids = production.bom_id.bom_line_ids.product_id

    def _inverse_move_line_raw_ids(self):
        for production in self:
            line_by_product = defaultdict(lambda: self.env['stock.move.line'])
            for line in production.move_line_raw_ids:
                line_by_product[line.product_id] |= line
            for move in production.move_raw_ids:
                move.move_line_ids = line_by_product.pop(move.product_id, self.env['stock.move.line'])
            for product_id, lines in line_by_product.items():
                qty = sum(line.product_uom_id._compute_quantity(line.quantity, product_id.uom_id) for line in lines)
                move = production._get_move_raw_values(product_id, qty, product_id.uom_id)
                move['additional'] = True
                production.move_raw_ids = [(0, 0, move)]
                production.move_raw_ids.filtered(lambda m: m.product_id == product_id)[:1].move_line_ids = lines

    def write(self, vals):
        if self.env.user._is_portal() and not self.env.su:
            unauthorized_fields = set(vals.keys()) - set(self._get_writeable_fields_portal_user())
            if unauthorized_fields:
                raise AccessError(_("You cannot write on fields %s in mrp.production.", ', '.join(unauthorized_fields)))

        if 'date_start' in vals and self.env.context.get('from_subcontract'):
            date_start = fields.Datetime.to_datetime(vals['date_start'])
            date_start_map = {
                prod: date_start - timedelta(days=prod.bom_id.produce_delay)
                if prod.bom_id else date_start
                for prod in self
            }
            res = True
            for production in self:
                res &= super(MrpProduction, production).write({**vals, 'date_start': date_start_map[production]})
            return res

        old_lots = [mo.lot_producing_ids for mo in self]
        if self.env.context.get('mrp_subcontracting') and 'product_qty' in vals:
            for mo in self:
                self.sudo().env['change.production.qty'].with_context(skip_activity=True, mrp_subcontracting=False, no_procurement=True).create([{
                    'mo_id': mo.id,
                    'product_qty': vals['product_qty'],
                }]).change_prod_qty()
                mo.sudo().action_assign()

        res = super().write(vals)

        if self.env.context.get('mrp_subcontracting') and ('product_qty' in vals or 'lot_producing_ids' in vals):
            for mo, old_lot in zip(self, old_lots):
                sbc_move = mo._get_subcontract_move()
                if not sbc_move:
                    continue
                if mo.product_tracking in ('lot', 'serial'):
                    sbc_move_lines = sbc_move.move_line_ids.filtered(lambda m: m.lot_id == old_lot)
                    sbc_move_line = sbc_move_lines[0]
                    sbc_move_line.quantity = mo.product_qty
                    sbc_move_line.lot_id = mo.lot_producing_ids
                    sbc_move_lines[1:].unlink()
                else:
                    sbc_move.quantity = mo.product_qty

        return res

    def action_merge(self):
        if any(production._get_subcontract_move() for production in self):
            raise ValidationError(_("Subcontracted manufacturing orders cannot be merged."))
        return super().action_merge()

    def pre_button_mark_done(self):
        if self._get_subcontract_move():
            return super(MrpProduction, self.with_context(skip_consumption=True)).pre_button_mark_done()
        return super().pre_button_mark_done()

    def _should_postpone_date_finished(self, date_finished):
        return super()._should_postpone_date_finished(date_finished) and not self._get_subcontract_move()

    def _has_workorders(self):
        if self.subcontractor_id:
            return False
        else:
            return super()._has_workorders()

    def _get_subcontract_move(self):
        return self.move_finished_ids.move_dest_ids.filtered(lambda m: m.is_subcontract)

    def _get_writeable_fields_portal_user(self):
        return ['move_line_raw_ids', 'lot_producing_ids', 'qty_producing', 'product_qty']

    def action_split_subcontracting(self):
        self.ensure_one()
        if not self.lot_producing_ids:
            raise UserError(_("Please set a lot/serial for the currently opened subcontracting MO first."))
        move = self._get_subcontract_move()
        if not move:
            return False
        if move.state == 'done':
            raise UserError(_("The subcontracted goods have already been received."))
        if all(l.lot_id for l in move.move_line_ids):
            move.move_line_ids.create({
                'product_id': move.product_id.id,
                'move_id': move.id,
                'quantity': 1,
                'lot_id': False,
            })
        return move.action_show_subcontract_details(lot_id=False)
