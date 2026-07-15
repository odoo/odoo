# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from collections import defaultdict
from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.tools.float_utils import float_is_zero
from odoo.tools.misc import OrderedSet


class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    _rec_names_search = ['name', 'incoming_picking.name']

    move_line_raw_ids = fields.One2many(
        'stock.move.line', string="Detail Component", readonly=False,
        inverse='_inverse_move_line_raw_ids', compute='_compute_move_line_raw_ids'
    )
    subcontracting_has_been_recorded = fields.Boolean("Has been recorded?", copy=False)
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
        line_ids_to_delete = set()
        for production in self:
            line_by_product = defaultdict(lambda: self.env['stock.move.line'])
            for line in production.move_line_raw_ids:
                line_by_product[line.product_id] |= line
            for move in production.move_raw_ids:
                lines = line_by_product.pop(move.product_id, self.env['stock.move.line'])
                lines_to_delete = move.move_line_ids - lines
                line_ids_to_delete.update(lines_to_delete.ids)
                move.move_line_ids = lines
            for product_id, lines in line_by_product.items():
                qty = sum(line.product_uom_id._compute_quantity(line.quantity, product_id.uom_id) for line in lines)
                move = production._get_move_raw_values(product_id, qty, product_id.uom_id)
                move['additional'] = True
                production.move_raw_ids = [(0, 0, move)]
                move = production.move_raw_ids.filtered(lambda m: m.product_id == product_id)[:1]
                lines_to_delete = move.move_line_ids - lines
                line_ids_to_delete.update(lines_to_delete.ids)
                move.move_line_ids = lines
        self.env['stock.move.line'].browse(line_ids_to_delete).unlink()

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

        return super().write(vals)

    def action_merge(self):
        if any(production._get_subcontract_move() for production in self):
            raise ValidationError(_("Subcontracted manufacturing orders cannot be merged."))
        return super().action_merge()

    def subcontracting_record_component(self):
        self.ensure_one()
        self.move_raw_ids.picked = True
        if not self._get_subcontract_move():
            raise UserError(_("This MO isn't related to a subcontracted move"))
        if float_is_zero(self.qty_producing, precision_rounding=self.product_uom_id.rounding):
            return {'type': 'ir.actions.act_window_close'}

        if self.move_raw_ids and not any(self.move_raw_ids.mapped('quantity')):
            raise UserError(_("You must indicate a non-zero amount consumed for at least one of your components"))
        consumption_issues = self._get_consumption_issues()
        if consumption_issues:
            return self._action_generate_consumption_wizard(consumption_issues)
        self.sudo()._update_finished_move()  # Portal user may need sudo rights to update pickings
        self.subcontracting_has_been_recorded = True

        quantity_issues = self._get_quantity_produced_issues()
        if quantity_issues:
            backorder = self.sudo()._split_productions()[1:]
            # No qty to consume to avoid propagate additional move
            # TODO avoid : stock move created in backorder with 0 as qty
            backorder.move_raw_ids.filtered(lambda m: m.additional).product_uom_qty = 0.0

            backorder.qty_producing = backorder.product_qty
            backorder._set_qty_producing()

            self.product_qty = self.qty_producing
            action = self._get_subcontract_move().filtered(lambda m: m.state not in ('done', 'cancel'))._action_record_components()
            action['res_id'] = backorder.id
            return action
        return {'type': 'ir.actions.act_window_close'}

    def pre_button_mark_done(self):
        if self._get_subcontract_move():
            return super(MrpProduction, self.with_context(skip_consumption=True)).pre_button_mark_done()
        return super().pre_button_mark_done()

    def _should_postpone_date_finished(self, date_finished):
        return super()._should_postpone_date_finished(date_finished) and not self._get_subcontract_move()

    def _update_finished_move(self):
        """ After producing, set the move line on the subcontract picking. """
        self.ensure_one()
        subcontract_move = self._get_subcontract_move().filtered(lambda m: m.state not in ('done', 'cancel'))
        if not subcontract_move:
            return
        move_uom = subcontract_move.product_uom
        lot_name = self.lot_producing_id.name
        qty_to_reserve, recorded_lot_names = 0, set()
        for production in self | subcontract_move._get_recorded_subcontract_production():
            production_lot_name = production.lot_producing_id.name
            if production_lot_name:
                recorded_lot_names.add(production_lot_name)
            if production_lot_name == lot_name:
                qty_to_reserve += production.product_uom_id._compute_quantity(
                    production.qty_producing, move_uom, rounding_method='HALF-UP')
        # Reservations for other recorded lots are left untouched others are obsolete.
        sml_to_update, reserved_qty, obsolete_sml_ids = self.env['stock.move.line'], 0, OrderedSet()
        for sml in subcontract_move.move_line_ids:
            sml_lot_name = sml.lot_id.name or sml.lot_name or False
            if sml_lot_name != lot_name:
                if sml_lot_name not in recorded_lot_names:
                    obsolete_sml_ids.add(sml.id)
                continue
            sml_to_update = sml
            reserved_qty = min(sml.product_uom_id._compute_quantity(sml.quantity, move_uom, rounding_method='HALF-UP'), qty_to_reserve)
            qty_to_reserve -= reserved_qty
            if float_is_zero(reserved_qty, precision_rounding=move_uom.rounding):
                obsolete_sml_ids.add(sml.id)
            else:
                sml.quantity = move_uom._compute_quantity(reserved_qty, sml.product_uom_id, rounding_method='HALF-UP')
        if not float_is_zero(qty_to_reserve, precision_rounding=move_uom.rounding):
            # Reuse sml to keep ids, prefering the one with the appropriate lot or none at all
            sml_to_update = sml_to_update or self.env['stock.move.line'].browse(obsolete_sml_ids).sorted(lambda ml: bool(ml.lot_id or ml.lot_name))[:1]
            obsolete_sml_ids.difference_update(sml_to_update.ids)
            if sml_to_update:
                sml_to_update.write({
                    'lot_id': self.lot_producing_id.id,
                    'lot_name': self.lot_producing_id.name,
                    'quantity': move_uom._compute_quantity(reserved_qty + qty_to_reserve, sml_to_update.product_uom_id, rounding_method='HALF-UP'),
                })
            else:
                product_qty = move_uom._compute_quantity(qty_to_reserve, self.product_id.uom_id, rounding_method='HALF-UP')
                self.env['stock.move.line'].create({
                    **subcontract_move._prepare_move_line_vals(quantity=product_qty),
                    'lot_id': self.lot_producing_id.id,
                })
        self.env['stock.move.line'].browse(obsolete_sml_ids).unlink()
        subcontract_move._recompute_state()

    def _subcontracting_filter_to_done(self):
        """ Filter subcontracting production where composant is already recorded and should be consider to be validate """
        def filter_in(mo):
            if mo.state in ('done', 'cancel'):
                return False
            if not mo.subcontracting_has_been_recorded:
                return False
            return True

        return self.filtered(filter_in)

    def _has_been_recorded(self):
        self.ensure_one()
        if self.state in ('cancel', 'done'):
            return True
        return self.subcontracting_has_been_recorded

    def _has_tracked_component(self):
        return any(m.has_tracking != 'none' for m in self.move_raw_ids)

    def _has_workorders(self):
        if self.subcontractor_id:
            return False
        else:
            return super()._has_workorders()

    def _get_subcontract_move(self):
        return self.move_finished_ids.move_dest_ids.filtered(lambda m: m.is_subcontract)

    def _get_writeable_fields_portal_user(self):
        return ['move_line_raw_ids', 'lot_producing_id', 'subcontracting_has_been_recorded', 'qty_producing', 'product_qty']

    def _subcontract_sanity_check(self):
        for production in self:
            if production.product_tracking != 'none' and not self.lot_producing_id:
                raise UserError(_('You must enter a serial number for %s', production.product_id.name))
            for sml in production.move_raw_ids.move_line_ids:
                if sml.tracking != 'none' and not sml.lot_id:
                    raise UserError(_('You must enter a serial number for each line of %s', sml.product_id.display_name))
        return True
