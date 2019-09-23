# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero


class StockMove(models.Model):
    _inherit = 'stock.move'

    is_subcontract = fields.Boolean('The move is a subcontract receipt')
    show_subcontracting_details_visible = fields.Boolean(
        compute='_compute_show_subcontracting_details_visible'
    )

    def _compute_show_subcontracting_details_visible(self):
        """ Compute if the action button in order to see moves raw is visible """
        for move in self:
            if move.is_subcontract and move._has_tracked_subcontract_components() and\
                    not float_is_zero(move.quantity_done, precision_rounding=move.product_uom.rounding):
                move.show_subcontracting_details_visible = True
            else:
                move.show_subcontracting_details_visible = False

    def _compute_show_details_visible(self):
        """ If the move is subcontract and the components are tracked. Then the
        show details button is visible.
        """
        res = super(StockMove, self)._compute_show_details_visible()
        for move in self:
            if not move.is_subcontract:
                continue
            if not move._has_tracked_subcontract_components():
                continue
            move.show_details_visible = True
        return res

    def copy(self, default=None):
        self.ensure_one()
        if not self.is_subcontract or 'location_id' in default:
            return super(StockMove, self).copy(default=default)
        if not default:
            default = {}
        default['location_id'] = self.picking_id.location_id.id
        return super(StockMove, self).copy(default=default)

    def write(self, values):
        """ If the initial demand is updated then also update the linked
        subcontract order to the new quantity.
        """
        if 'product_uom_qty' in values:
            if self.env.context.get('cancel_backorder') is False:
                return super(StockMove, self).write(values)
            self.filtered(lambda m: m.is_subcontract and
            m.state not in ['draft', 'cancel', 'done'])._update_subcontract_order_qty(values['product_uom_qty'])
        return super(StockMove, self).write(values)

    def action_show_details(self):
        """ Open the produce wizard in order to register tracked components for
        subcontracted product. Otherwise use standard behavior.
        """
        self.ensure_one()
        if self.is_subcontract:
            rounding = self.product_uom.rounding
            production = self.move_orig_ids.production_id
            if self._has_tracked_subcontract_components() and\
                    float_compare(production.qty_produced, production.product_uom_qty, precision_rounding=rounding) < 0 and\
                    float_compare(self.quantity_done, self.product_uom_qty, precision_rounding=rounding) < 0:
                return self._action_record_components()
        action = super(StockMove, self).action_show_details()
        if self.is_subcontract:
            action['views'] = [(self.env.ref('stock.view_stock_move_operations').id, 'form')]
            action['context'].update({
                'show_lots_m2o': self.has_tracking != 'none',
                'show_lots_text': False,
            })
        return action

    def action_show_subcontract_details(self):
        """ Display moves raw for subcontracted product self. """
        moves = self.move_orig_ids.production_id.move_raw_ids
        tree_view = self.env.ref('mrp_subcontracting.mrp_subcontracting_move_tree_view')
        form_view = self.env.ref('mrp_subcontracting.mrp_subcontracting_move_form_view')
        return {
            'name': _('Raw Materials for %s') % (self.product_id.display_name),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'target': 'current',
            'domain': [('id', 'in', moves.ids)],
        }

    def _action_confirm(self, merge=True, merge_into=False):
        subcontract_details_per_picking = defaultdict(list)
        for move in self:
            if move.location_id.usage != 'supplier' or move.location_dest_id.usage == 'supplier':
                continue
            if move.move_orig_ids.production_id:
                continue
            bom = move._get_subcontract_bom()
            if not bom:
                continue
            if float_is_zero(move.product_qty, precision_rounding=move.product_uom.rounding) and\
                    move.picking_id.immediate_transfer is True:
                raise UserError(_("To subcontract, use a planned transfer."))
            subcontract_details_per_picking[move.picking_id].append((move, bom))
            move.write({
                'is_subcontract': True,
                'location_id': move.picking_id.partner_id.with_context(force_company=move.company_id.id).property_stock_subcontractor.id
            })
        for picking, subcontract_details in subcontract_details_per_picking.items():
            picking._subcontracted_produce(subcontract_details)

        res = super(StockMove, self)._action_confirm(merge=merge, merge_into=merge_into)
        if subcontract_details_per_picking:
            self.env['stock.picking'].concat(*list(subcontract_details_per_picking.keys())).action_assign()
        return res

    def _action_record_components(self):
        action = self.env.ref('mrp.act_mrp_product_produce').read()[0]
        action['context'] = dict(
            default_production_id=self.move_orig_ids.production_id.id,
            default_subcontract_move_id=self.id
        )
        return action

    def _check_overprocessed_subcontract_qty(self):
        """ If a subcontracted move use tracked components. Do not allow to add
        quantity without the produce wizard. Instead update the initial demand
        and use the register component button. Split or correct a lot/sn is
        possible.
        """
        overprocessed_moves = self.env['stock.move']
        for move in self:
            if not move.is_subcontract:
                continue
            # Extra quantity is allowed when components do not need to be register
            if not move._has_tracked_subcontract_components():
                continue
            rounding = move.product_uom.rounding
            if float_compare(move.quantity_done, move.move_orig_ids.production_id.qty_produced, precision_rounding=rounding) > 0:
                overprocessed_moves |= move
        if overprocessed_moves:
            raise UserError(_("""
You have to use 'Records Components' button in order to register quantity for a
subcontracted product(s) with tracked component(s):
 %s.
If you want to process more than initially planned, you
can use the edit + unlock buttons in order to adapt the initial demand on the
operations.""") % ('\n'.join(overprocessed_moves.mapped('product_id.display_name'))))

    def _get_subcontract_bom(self):
        self.ensure_one()
        bom = self.env['mrp.bom'].sudo()._bom_subcontract_find(
            product=self.product_id,
            picking_type=self.picking_type_id,
            company_id=self.company_id.id,
            bom_type='subcontract',
            subcontractor=self.picking_id.partner_id,
        )
        return bom

    def _has_tracked_subcontract_components(self):
        self.ensure_one()
        return any(m.has_tracking != 'none' for m in self.move_orig_ids.production_id.move_raw_ids)

    def _prepare_extra_move_vals(self, qty):
        vals = super(StockMove, self)._prepare_extra_move_vals(qty)
        vals['location_id'] = self.location_id.id
        return vals

    def _prepare_move_split_vals(self, qty):
        vals = super(StockMove, self)._prepare_move_split_vals(qty)
        vals['location_id'] = self.location_id.id
        return vals

    def _should_bypass_reservation(self):
        """ If the move is subcontracted then ignore the reservation. """
        should_bypass_reservation = super(StockMove, self)._should_bypass_reservation()
        if not should_bypass_reservation and self.is_subcontract:
            return True
        return should_bypass_reservation

    def _update_subcontract_order_qty(self, quantity):
        for move in self:
            quantity_change = quantity - move.product_uom_qty
            production = move.move_orig_ids.production_id
            if production:
                self.env['change.production.qty'].with_context(skip_activity=True).create({
                    'mo_id': production.id,
                    'product_qty': production.product_uom_qty + quantity_change
                }).change_prod_qty()

