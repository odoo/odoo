# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from dateutil.relativedelta import relativedelta
from odoo import _, api, Command, fields, models
from odoo.osv import expression
from odoo.tools import float_compare, float_round, float_is_zero, OrderedSet
from odoo.exceptions import ValidationError


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    workorder_id = fields.Many2one('mrp.workorder', 'Work Order', check_company=True)
    production_id = fields.Many2one('mrp.production', 'Production Order', check_company=True)
    description_bom_line = fields.Char(related='move_id.description_bom_line')

    @api.depends('production_id')
    def _compute_picking_type_id(self):
        line_to_remove = self.env['stock.move.line']
        for line in self:
            if not line.production_id:
                continue
            line.picking_type_id = line.production_id.picking_type_id
            line_to_remove |= line
        return super(StockMoveLine, self - line_to_remove)._compute_picking_type_id()

    def _search_picking_type_id(self, operator, value):
        res = super()._search_picking_type_id(operator=operator, value=value)
        if operator in ['not in', '!=', 'not ilike']:
            if value is False:
                return expression.OR([[('production_id.picking_type_id', operator, value)], res])
            else:
                return expression.AND([[('production_id.picking_type_id', operator, value)], res])
        else:
            if value is False:
                return expression.AND([[('production_id.picking_type_id', operator, value)], res])
            else:
                return expression.OR([[('production_id.picking_type_id', operator, value)], res])

    @api.model_create_multi
    def create(self, values):
        res = super(StockMoveLine, self).create(values)
        for line in res:
            # If the line is added in a done production, we need to map it
            # manually to the produced move lines in order to see them in the
            # traceability report
            if line.move_id.raw_material_production_id and line.state == 'done':
                mo = line.move_id.raw_material_production_id
                finished_lots = mo.lot_producing_id
                finished_lots |= mo.move_finished_ids.filtered(lambda m: m.product_id != mo.product_id).move_line_ids.lot_id
                if finished_lots:
                    produced_move_lines = mo.move_finished_ids.move_line_ids.filtered(lambda sml: sml.lot_id in finished_lots)
                    line.produce_line_ids = [(6, 0, produced_move_lines.ids)]
                else:
                    produced_move_lines = mo.move_finished_ids.move_line_ids
                    line.produce_line_ids = [(6, 0, produced_move_lines.ids)]
        return res

    def _get_similar_move_lines(self):
        lines = super(StockMoveLine, self)._get_similar_move_lines()
        if self.move_id.production_id:
            finished_moves = self.move_id.production_id.move_finished_ids
            finished_move_lines = finished_moves.mapped('move_line_ids')
            lines |= finished_move_lines.filtered(lambda ml: ml.product_id == self.product_id and (ml.lot_id or ml.lot_name))
        if self.move_id.raw_material_production_id:
            raw_moves = self.move_id.raw_material_production_id.move_raw_ids
            raw_moves_lines = raw_moves.mapped('move_line_ids')
            lines |= raw_moves_lines.filtered(lambda ml: ml.product_id == self.product_id and (ml.lot_id or ml.lot_name))
        return lines

    def write(self, vals):
        for move_line in self:
            production = move_line.move_id.production_id or move_line.move_id.raw_material_production_id
            if production and move_line.state == 'done' and any(field in vals for field in ('lot_id', 'location_id', 'quantity')):
                move_line._log_message(production, move_line, 'mrp.track_production_move_template', vals)
        return super(StockMoveLine, self).write(vals)

    def _get_aggregated_properties(self, move_line=False, move=False):
        aggregated_properties = super()._get_aggregated_properties(move_line, move)
        bom = aggregated_properties['move'].bom_line_id.bom_id
        aggregated_properties['bom'] = bom or False
        aggregated_properties['line_key'] += f'_{bom.id if bom else ""}'
        return aggregated_properties

    def _compute_product_packaging_qty(self):
        # we catch kit lines where the packaging is still the one from the final product (it has
        # not been changed to a packaging of a component)
        kit_lines = self.filtered(lambda move_line: move_line.move_id.bom_line_id.bom_id.type == 'phantom' and
        move_line.move_id.product_packaging_id and move_line.product_id != move_line.move_id.product_packaging_id.product_id)
        for move_line in kit_lines:
            move = move_line.move_id
            bom_line = move.bom_line_id
            kit_bom = bom_line.bom_id

            # Convert the move line quantity to the product's move uom
            qty_move_uom = move_line.product_uom_id._compute_quantity(move_line.quantity, move_line.move_id.product_uom)
            # Convert the product's move uom to the bom line's uom
            qty_bom_uom = move.product_uom._compute_quantity(qty_move_uom, bom_line.product_uom_id)
            # calculate the bom's kit qty in kit product uom qty
            bom_qty_product_uom = kit_bom.product_uom_id._compute_quantity(kit_bom.product_qty, kit_bom.product_tmpl_id.uom_id)
            # calculate the comp/final_prod ratio of the BOM
            kit_ratio = bom_line.product_qty / bom_qty_product_uom
            # calculate the number of kit on the move line according to the number of comp
            kit_qty = qty_bom_uom / kit_ratio
            # calculate the quantity needed of packaging
            move_line.product_packaging_qty = kit_qty / move_line.move_id.product_packaging_id.qty
        super(StockMoveLine, self - kit_lines)._compute_product_packaging_qty()

    @api.model
    def _compute_packaging_qtys(self, aggregated_move_lines):
        non_kit_ml = {}
        kit_aggregated_ml = set()
        kit_moves = defaultdict(lambda: self.env['stock.move'])
        kit_qty = {}

        for line in aggregated_move_lines.values():
            if line['packaging']:
                bom_id = line['bom']
                if bom_id and bom_id.type == "phantom":
                    kit_aggregated_ml.add(line['line_key'])
                    kit_moves[bom_id] |= line['move']
                else:
                    non_kit_ml[line['line_key']] = line

        filters = {'incoming_moves': lambda m: True, 'outgoing_moves': lambda m: False}
        for bom, moves in kit_moves.items():
            if moves.picking_id.backorder_ids:
                kit_qty_ordered = (moves + moves.picking_id.backorder_ids.move_ids)._compute_kit_quantities(bom.product_id or bom.product_tmpl_id.product_variant_id, 1, bom, filters)
                kit_qty_done = moves._compute_kit_quantities(bom.product_id or bom.product_tmpl_id.product_variant_id, 1, bom, filters)
            else:
                kit_qty_done = moves._compute_kit_quantities(bom.product_id or bom.product_tmpl_id.product_variant_id, 1, bom, filters)
                kit_qty_ordered = kit_qty_done
            kit_qty[bom.id] = (kit_qty_ordered, kit_qty_done)

        for key in kit_aggregated_ml:
            line = aggregated_move_lines[key]
            bom_id = line['bom']
            kit_qty_ordered, kit_qty_done = kit_qty[bom_id.id]
            if line['packaging'].product_id == line['product']:
                # If packaging has been set directly on the move
                line['packaging_qty'] = line['packaging']._compute_qty(line['qty_ordered'], line['product_uom'])
                line['packaging_quantity'] = line['packaging']._compute_qty(line['quantity'], line['product_uom'])
            else:
                # If packaging comes from the kit
                line['packaging_qty'] = line['packaging']._compute_qty(kit_qty_ordered, bom_id.product_uom_id)
                line['packaging_quantity'] = line['packaging']._compute_qty(kit_qty_done, bom_id.product_uom_id)
            aggregated_move_lines[key] = line

        non_kit_ml = super()._compute_packaging_qtys(non_kit_ml)
        for line in non_kit_ml.values():
            aggregated_move_lines[line['line_key']] = line

        return aggregated_move_lines

    def _get_aggregated_product_quantities(self, **kwargs):
        """Returns dictionary of products and corresponding values of interest grouped by optional kit_name

        Removes descriptions where description == kit_name. kit_name is expected to be passed as a
        kwargs value because this is not directly stored in move_line_ids. Unfortunately because we
        are working with aggregated data, we have to loop through the aggregation to do this removal.

        arguments: kit_name (optional): string value of a kit name passed as a kwarg
        returns: dictionary {same_key_as_super: {same_values_as_super, ...}
        """
        aggregated_move_lines = super()._get_aggregated_product_quantities(**kwargs)
        kit_name = kwargs.get('kit_name')

        to_be_removed = []
        for aggregated_move_line in aggregated_move_lines:
            bom = aggregated_move_lines[aggregated_move_line]['bom']
            is_phantom = bom.type == 'phantom' if bom else False
            if kit_name:
                product = bom.product_id or bom.product_tmpl_id if bom else False
                display_name = product.display_name if product else False
                description = aggregated_move_lines[aggregated_move_line]['description']
                if not is_phantom or display_name != kit_name:
                    to_be_removed.append(aggregated_move_line)
                elif description == kit_name:
                    aggregated_move_lines[aggregated_move_line]['description'] = ""
            elif not kwargs and is_phantom:
                to_be_removed.append(aggregated_move_line)

        for move_line in to_be_removed:
            del aggregated_move_lines[move_line]

        return aggregated_move_lines

    def _prepare_stock_move_vals(self):
        move_vals = super()._prepare_stock_move_vals()
        if self.env['product.product'].browse(move_vals['product_id']).is_kits:
            move_vals['location_id'] = self.location_id.id
            move_vals['location_dest_id'] = self.location_dest_id.id
        return move_vals

    def _get_linkable_moves(self):
        """ Don't linke move lines with kit products to moves with dissimilar locations so that
        post `action_explode()` move lines will have accurate location data.
        """
        self.ensure_one()
        if self.product_id and self.product_id.is_kits:
            moves = self.picking_id.move_ids.filtered(lambda move:
                move.product_id == self.product_id and
                move.location_id == self.location_id and
                move.location_dest_id == self.location_dest_id
            )
            return sorted(moves, key=lambda m: m.quantity < m.product_qty, reverse=True)
        else:
            return super()._get_linkable_moves()

    def _exclude_requiring_lot(self):
        return (self.move_id.unbuild_id and not self.move_id.origin_returned_move_id.move_line_ids.lot_id) or super()._exclude_requiring_lot()


class StockMove(models.Model):
    _inherit = 'stock.move'

    created_production_id = fields.Many2one('mrp.production', 'Created Production Order', check_company=True, index=True)
    production_id = fields.Many2one(
        'mrp.production', 'Production Order for finished products', check_company=True, index='btree_not_null')
    raw_material_production_id = fields.Many2one(
        'mrp.production', 'Production Order for components', check_company=True, index='btree_not_null')
    unbuild_id = fields.Many2one(
        'mrp.unbuild', 'Disassembly Order', check_company=True)
    consume_unbuild_id = fields.Many2one(
        'mrp.unbuild', 'Consumed Disassembly Order', check_company=True)
    allowed_operation_ids = fields.One2many(
        'mrp.routing.workcenter', related='raw_material_production_id.bom_id.operation_ids')
    operation_id = fields.Many2one(
        'mrp.routing.workcenter', 'Operation To Consume', check_company=True,
        domain="[('id', 'in', allowed_operation_ids)]")
    workorder_id = fields.Many2one(
        'mrp.workorder', 'Work Order To Consume', copy=False, check_company=True, index='btree_not_null')
    # Quantities to process, in normalized UoMs
    bom_line_id = fields.Many2one('mrp.bom.line', 'BoM Line', check_company=True)
    byproduct_id = fields.Many2one(
        'mrp.bom.byproduct', 'By-products', check_company=True,
        help="By-product line that generated the move in a manufacturing order")
    unit_factor = fields.Float('Unit Factor', compute='_compute_unit_factor', store=True)
    is_done = fields.Boolean(
        'Done', compute='_compute_is_done', store=True)
    order_finished_lot_id = fields.Many2one('stock.lot', string="Finished Lot/Serial Number", related="raw_material_production_id.lot_producing_id", store=True, index='btree_not_null')
    should_consume_qty = fields.Float('Quantity To Consume', compute='_compute_should_consume_qty', digits='Product Unit of Measure')
    cost_share = fields.Float(
        "Cost Share (%)", digits=(5, 2),  # decimal = 2 is important for rounding calculations!!
        help="The percentage of the final production cost for this by-product. The total of all by-products' cost share must be smaller or equal to 100.")
    product_qty_available = fields.Float('Product On Hand Quantity', related='product_id.qty_available', depends=['product_id'])
    product_virtual_available = fields.Float('Product Forecasted Quantity', related='product_id.virtual_available', depends=['product_id'])
    description_bom_line = fields.Char('Kit', compute='_compute_description_bom_line')
    manual_consumption = fields.Boolean(
        'Manual Consumption', compute='_compute_manual_consumption', store=True, readonly=False,
        help="When activated, then the registration of consumption for that component is recorded manually exclusively.\n"
             "If not activated, and any of the components consumption is edited manually on the manufacturing order, Odoo assumes manual consumption also.")

    @api.depends('product_id')
    def _compute_manual_consumption(self):
        for move in self:
            # when computed for new_id in onchange, use value from _origin
            if move != move._origin:
                move.manual_consumption = move._origin.manual_consumption
            elif not move.manual_consumption:
                move.manual_consumption = move._is_manual_consumption()

    @api.depends('raw_material_production_id.location_src_id', 'production_id.location_src_id')
    def _compute_location_id(self):
        ids_to_super = set()
        for move in self:
            if move.production_id:
                move.location_id = move.product_id.with_company(move.company_id).property_stock_production.id
            elif move.raw_material_production_id:
                move.location_id = move.raw_material_production_id.location_src_id
            else:
                ids_to_super.add(move.id)
        return super(StockMove, self.browse(ids_to_super))._compute_location_id()

    @api.depends('raw_material_production_id.location_dest_id', 'production_id.location_dest_id')
    def _compute_location_dest_id(self):
        ids_to_super = set()
        for move in self:
            if move.production_id:
                move.location_dest_id = move.production_id.location_dest_id
            elif move.raw_material_production_id:
                move.location_dest_id = move.product_id.with_company(move.company_id).property_stock_production.id
            else:
                ids_to_super.add(move.id)
        return super(StockMove, self.browse(ids_to_super))._compute_location_dest_id()

    @api.depends('bom_line_id')
    def _compute_description_bom_line(self):
        bom_line_description = {}
        for bom in self.bom_line_id.bom_id:
            if bom.type != 'phantom':
                continue
            line_ids = self.bom_line_id.filtered(lambda line: line.bom_id == bom).mapped('id')
            total = len(line_ids)
            for i, line_id in enumerate(line_ids):
                bom_line_description[line_id] = '%s - %d/%d' % (bom.display_name, i + 1, total)

        for move in self:
            move.description_bom_line = bom_line_description.get(move.bom_line_id.id, move.description_bom_line)

    @api.depends('raw_material_production_id.priority')
    def _compute_priority(self):
        super()._compute_priority()
        for move in self:
            move.priority = move.raw_material_production_id.priority or move.priority or '0'

    @api.depends('raw_material_production_id.picking_type_id', 'production_id.picking_type_id')
    def _compute_picking_type_id(self):
        super()._compute_picking_type_id()
        for move in self:
            if move.raw_material_production_id or move.production_id:
                move.picking_type_id = (move.raw_material_production_id or move.production_id).picking_type_id

    @api.depends('raw_material_production_id.is_locked', 'production_id.is_locked')
    def _compute_is_locked(self):
        super(StockMove, self)._compute_is_locked()
        for move in self:
            if move.raw_material_production_id:
                move.is_locked = move.raw_material_production_id.is_locked
            if move.production_id:
                move.is_locked = move.production_id.is_locked

    @api.depends('state')
    def _compute_is_done(self):
        for move in self:
            move.is_done = (move.state in ('done', 'cancel'))

    @api.depends('product_uom_qty',
        'raw_material_production_id', 'raw_material_production_id.product_qty', 'raw_material_production_id.qty_produced',
        'production_id', 'production_id.product_qty', 'production_id.qty_produced')
    def _compute_unit_factor(self):
        for move in self:
            mo = move.raw_material_production_id or move.production_id
            if mo:
                move.unit_factor = move.product_uom_qty / ((mo.product_qty - mo.qty_produced) or 1)
            else:
                move.unit_factor = 1.0

    @api.depends('raw_material_production_id', 'raw_material_production_id.name', 'production_id', 'production_id.name')
    def _compute_reference(self):
        moves_with_reference = self.env['stock.move']
        for move in self:
            if move.raw_material_production_id and move.raw_material_production_id.name:
                move.reference = move.raw_material_production_id.name
                moves_with_reference |= move
            if move.production_id and move.production_id.name:
                move.reference = move.production_id.name
                moves_with_reference |= move
        super(StockMove, self - moves_with_reference)._compute_reference()

    @api.depends('raw_material_production_id.qty_producing', 'product_uom_qty', 'product_uom')
    def _compute_should_consume_qty(self):
        for move in self:
            mo = move.raw_material_production_id
            if not mo or not move.product_uom:
                move.should_consume_qty = 0
                continue
            move.should_consume_qty = float_round((mo.qty_producing - mo.qty_produced) * move.unit_factor, precision_rounding=move.product_uom.rounding)

    @api.depends('byproduct_id')
    def _compute_show_info(self):
        super()._compute_show_info()
        byproduct_moves = self.filtered(lambda m: m.byproduct_id or m in self.production_id.move_finished_ids)
        byproduct_moves.show_quant = False
        byproduct_moves.show_lots_m2o = True

    @api.depends('picking_type_id.use_create_components_lots')
    def _compute_display_assign_serial(self):
        super()._compute_display_assign_serial()
        for move in self:
            if move.display_import_lot \
                    and move.raw_material_production_id \
                    and not move.raw_material_production_id.picking_type_id.use_create_components_lots:
                move.display_import_lot = False
                move.display_assign_serial = False

    @api.onchange('product_uom_qty', 'product_uom')
    def _onchange_product_uom_qty(self):
        if self.product_uom and self.raw_material_production_id and self.has_tracking == 'none':
            mo = self.raw_material_production_id
            new_qty = float_round((mo.qty_producing - mo.qty_produced) * self.unit_factor, precision_rounding=self.product_uom.rounding)
            self.quantity = new_qty

    @api.onchange('quantity', 'product_uom', 'picked')
    def _onchange_quantity(self):
        if self.raw_material_production_id and not self.manual_consumption and self.picked and self.product_uom and \
           float_compare(self.product_uom_qty, self.quantity, precision_rounding=self.product_uom.rounding) != 0:
            self.manual_consumption = True

    @api.constrains('quantity', 'raw_material_production_id')
    def _check_negative_quantity(self):
        for move in self:
            if move.raw_material_production_id and float_compare(move.quantity, 0, precision_rounding=move.product_uom.rounding) < 0:
                raise ValidationError(_("Please enter a positive quantity."))

    @api.model
    def default_get(self, fields_list):
        defaults = super(StockMove, self).default_get(fields_list)
        if self.env.context.get('default_raw_material_production_id') or self.env.context.get('default_production_id'):
            production_id = self.env['mrp.production'].browse(self.env.context.get('default_raw_material_production_id') or self.env.context.get('default_production_id'))
            if production_id.state not in ('draft', 'cancel'):
                if production_id.state != 'done':
                    defaults['state'] = 'draft'
                else:
                    defaults['state'] = 'done'
                    defaults['additional'] = True
                defaults['product_uom_qty'] = 0.0
            elif production_id.state == 'draft':
                defaults['group_id'] = production_id.procurement_group_id.id
                defaults['reference'] = production_id.name
        return defaults

    @api.model_create_multi
    def create(self, vals_list):
        """ Enforce consistent values (i.e. match _get_move_raw_values/_get_move_finished_values) for:
        - Manually added components/byproducts specifically values we can't set via view with "default_"
        - Moves from a copied MO
        - Backorders
        """
        if self.env.context.get('force_manual_consumption'):
            for vals in vals_list:
                vals['manual_consumption'] = True
        mo_id_to_mo = defaultdict(lambda: self.env['mrp.production'])
        product_id_to_product = defaultdict(lambda: self.env['product.product'])
        for values in vals_list:
            mo_id = values.get('raw_material_production_id', False) or values.get('production_id', False)
            location_dest = self.env['stock.location'].browse(values.get('location_dest_id'))
            if mo_id and not values.get('scrapped') and not location_dest.scrap_location:
                mo = mo_id_to_mo[mo_id]
                if not mo:
                    mo = mo.browse(mo_id)
                    mo_id_to_mo[mo_id] = mo
                values['name'] = mo.name
                values['origin'] = mo._get_origin()
                values['group_id'] = mo.procurement_group_id.id
                values['propagate_cancel'] = mo.propagate_cancel
                if values.get('raw_material_production_id', False):
                    product = product_id_to_product[values['product_id']]
                    if not product:
                        product = product.browse(values['product_id'])
                    product_id_to_product[values['product_id']] = product
                    values['location_dest_id'] = mo.production_location_id.id
                    if not values.get('location_id'):
                        values['location_id'] = mo.location_src_id.id
                    if mo.state in ['progress', 'to_close'] and mo.qty_producing > 0:
                        values['picked'] = True
                    continue
                # produced products + byproducts
                values['location_id'] = mo.production_location_id.id
                values['date'] = mo.date_finished
                values['date_deadline'] = mo.date_deadline
                if not values.get('location_dest_id'):
                    values['location_dest_id'] = mo.location_dest_id.id
                if not values.get('location_final_id'):
                    values['location_final_id'] = mo.warehouse_id.lot_stock_id.id
        return super().create(vals_list)

    def write(self, vals):
        if 'product_id' in vals:
            move_to_unlink = self.filtered(lambda m: m.product_id.id != vals.get('product_id'))
            other_move = self - move_to_unlink
            if move_to_unlink.production_id and move_to_unlink.state not in ['draft', 'cancel', 'done']:
                moves_data = move_to_unlink.copy_data()
                for move_data in moves_data:
                    move_data.update({'product_id': vals.get('product_id')})
                updated_product_move = self.create(moves_data)
                updated_product_move._action_confirm()
                move_to_unlink.unlink()
                self = other_move + updated_product_move
        if self.env.context.get('force_manual_consumption'):
            vals['manual_consumption'] = True
        if 'product_uom_qty' in vals and 'move_line_ids' in vals:
            # first update lines then product_uom_qty as the later will unreserve
            # so possibly unlink lines
            move_line_vals = vals.pop('move_line_ids')
            super().write({'move_line_ids': move_line_vals})
        old_demand = {move.id: move.product_uom_qty for move in self}
        res = super().write(vals)
        if 'product_uom_qty' in vals and not self.env.context.get('no_procurement', False):
            # when updating consumed qty need to update related pickings
            # context no_procurement means we don't want the qty update to modify stock i.e create new pickings
            # ex. when spliting MO to backorders we don't want to move qty from pre prod to stock in 2/3 step config
            self.filtered(lambda m: m.raw_material_production_id.state in ('confirmed', 'progress', 'to_close'))._run_procurement(old_demand)
        return res

    def _run_procurement(self, old_qties=False):
        procurements = []
        old_qties = old_qties or {}
        to_assign = self.env['stock.move']
        self._adjust_procure_method()
        for move in self:
            if float_compare(move.product_uom_qty - old_qties.get(move.id, 0), 0, precision_rounding=move.product_uom.rounding) < 0\
                    and move.procure_method == 'make_to_order'\
                    and all(m.state == 'done' for m in move.move_orig_ids):
                continue
            if float_compare(move.product_uom_qty, 0, precision_rounding=move.product_uom.rounding) > 0:
                if move._should_bypass_reservation() \
                        or move.picking_type_id.reservation_method == 'at_confirm' \
                        or (move.reservation_date and move.reservation_date <= fields.Date.today()):
                    to_assign |= move

            if move.procure_method == 'make_to_order':
                procurement_qty = move.product_uom_qty - old_qties.get(move.id, 0)
                possible_reduceable_qty = -sum(move.move_orig_ids.filtered(lambda m: m.state not in ('done', 'cancel') and m.product_uom_qty).mapped('product_uom_qty'))
                procurement_qty = max(procurement_qty, possible_reduceable_qty)
                values = move._prepare_procurement_values()
                origin = move._prepare_procurement_origin()
                procurements.append(self.env['procurement.group'].Procurement(
                    move.product_id, procurement_qty, move.product_uom,
                    move.location_id, move.name, origin, move.company_id, values))

        to_assign._action_assign()
        if procurements:
            self.env['procurement.group'].run(procurements)

    def _action_assign(self, force_qty=False):
        res = super(StockMove, self)._action_assign(force_qty=force_qty)
        for move in self.filtered(lambda x: x.production_id or x.raw_material_production_id):
            if move.move_line_ids:
                move.move_line_ids.write({'production_id': move.raw_material_production_id.id,
                                               'workorder_id': move.workorder_id.id,})
        return res

    def _action_confirm(self, merge=True, merge_into=False):
        moves = self.action_explode()
        merge_into = merge_into and merge_into.action_explode()
        # we go further with the list of ids potentially changed by action_explode
        return super(StockMove, moves)._action_confirm(merge=merge, merge_into=merge_into)

    def _action_done(self, cancel_backorder=False):
        # explode kit moves that avoided the action_explode of any confirmation process
        moves_to_explode = self.filtered(lambda m: m.product_id.is_kits and m.state not in ('draft', 'cancel'))
        exploded_moves = moves_to_explode.action_explode()
        moves = (self - moves_to_explode) | exploded_moves
        return super(StockMove, moves)._action_done(cancel_backorder)

    def _should_bypass_reservation(self, forced_location=False):
        return super()._should_bypass_reservation(forced_location) or self.product_id.with_company(self.company_id).is_kits

    def action_explode(self):
        """ Explodes pickings """
        # in order to explode a move, we must have a picking_type_id on that move because otherwise the move
        # won't be assigned to a picking and it would be weird to explode a move into several if they aren't
        # all grouped in the same picking.
        moves_ids_to_return = OrderedSet()
        moves_ids_to_unlink = OrderedSet()
        phantom_moves_vals_list = []
        for move in self:
            if (not move.picking_type_id and not (self.env.context.get('is_scrap') or self.env.context.get('skip_picking_assignation'))) or (move.production_id and move.production_id.product_id == move.product_id):
                moves_ids_to_return.add(move.id)
                continue
            bom = self.env['mrp.bom'].sudo()._bom_find(move.product_id, company_id=move.company_id.id, bom_type='phantom')[move.product_id]
            if not bom:
                moves_ids_to_return.add(move.id)
                continue
            if float_is_zero(move.product_uom_qty, precision_rounding=move.product_uom.rounding):
                factor = move.product_uom._compute_quantity(move.quantity, bom.product_uom_id) / bom.product_qty
            else:
                factor = move.product_uom._compute_quantity(move.product_uom_qty, bom.product_uom_id) / bom.product_qty
            _dummy, lines = bom.sudo().explode(move.product_id, factor, picking_type=bom.picking_type_id, never_attribute_values=move.never_product_template_attribute_value_ids)
            for bom_line, line_data in lines:
                if float_is_zero(move.product_uom_qty, precision_rounding=move.product_uom.rounding) or self.env.context.get('is_scrap'):
                    phantom_moves_vals_list += move._generate_move_phantom(bom_line, 0, line_data['qty'])
                else:
                    phantom_moves_vals_list += move._generate_move_phantom(bom_line, line_data['qty'], 0)
            # delete the move with original product which is not relevant anymore
            moves_ids_to_unlink.add(move.id)

        if phantom_moves_vals_list:
            phantom_moves = self.env['stock.move'].create(phantom_moves_vals_list)
            phantom_moves._adjust_procure_method()
            moves_ids_to_return |= phantom_moves.action_explode().ids
        move_to_unlink = self.env['stock.move'].browse(moves_ids_to_unlink).sudo()
        move_to_unlink.quantity = 0
        move_to_unlink._action_cancel()
        move_to_unlink.unlink()
        return self.env['stock.move'].browse(moves_ids_to_return)

    def action_show_details(self):
        self.ensure_one()
        action = super().action_show_details()
        if self.raw_material_production_id:
            action['views'] = [(self.env.ref('mrp.view_stock_move_operations_raw').id, 'form')]
            action['context']['show_destination_location'] = False
            action['context']['force_manual_consumption'] = True
            action['context']['active_mo_id'] = self.raw_material_production_id.id
        elif self.production_id:
            action['views'] = [(self.env.ref('mrp.view_stock_move_operations_finished').id, 'form')]
            action['context']['show_source_location'] = False
            action['context']['show_reserved_quantity'] = False
        return action

    def action_add_from_catalog_raw(self):
        mo = self.env['mrp.production'].browse(self.env.context.get('order_id'))
        return mo.with_context(child_field='move_raw_ids').action_add_from_catalog()

    def action_add_from_catalog_byproduct(self):
        mo = self.env['mrp.production'].browse(self.env.context.get('order_id'))
        return mo.with_context(child_field='move_byproduct_ids').action_add_from_catalog()

    def _action_cancel(self):
        res = super(StockMove, self)._action_cancel()
        if not 'skip_mo_check' in self.env.context:
            mo_to_cancel = self.mapped('raw_material_production_id').filtered(lambda p: all(m.state == 'cancel' for m in p.move_raw_ids))
            if mo_to_cancel:
                mo_to_cancel._action_cancel()
        return res

    def _prepare_move_split_vals(self, qty):
        defaults = super()._prepare_move_split_vals(qty)
        defaults['workorder_id'] = False
        return defaults

    def _prepare_procurement_origin(self):
        self.ensure_one()
        if self.raw_material_production_id and self.raw_material_production_id.orderpoint_id:
            return self.origin
        return super()._prepare_procurement_origin()

    def _prepare_phantom_move_values(self, bom_line, product_qty, quantity_done):
        return {
            'picking_id': self.picking_id.id if self.picking_id else False,
            'product_id': bom_line.product_id.id,
            'product_uom': bom_line.product_uom_id.id,
            'product_uom_qty': product_qty,
            'quantity': quantity_done,
            'name': self.name,
            'picked': self.picked,
            'bom_line_id': bom_line.id,
        }

    def _generate_move_phantom(self, bom_line, product_qty, quantity_done):
        vals = []
        if bom_line.product_id.type == 'consu':
            vals = self.copy_data(default=self._prepare_phantom_move_values(bom_line, product_qty, quantity_done))
            if self.state == 'assigned':
                for v in vals:
                    v['state'] = 'assigned'
        return vals

    def _is_consuming(self):
        return super()._is_consuming() or self.picking_type_id.code == 'mrp_operation'

    def _get_backorder_move_vals(self):
        self.ensure_one()
        return {
            'state': 'draft' if self.state == 'draft' else 'confirmed',
            'reservation_date': self.reservation_date,
            'date_deadline': self.date_deadline,
            'manual_consumption': self._is_manual_consumption(),
            'move_orig_ids': [Command.link(m.id) for m in self.mapped('move_orig_ids')],
            'move_dest_ids': [Command.link(m.id) for m in self.mapped('move_dest_ids')],
            'procure_method': self.procure_method,
        }

    def _get_source_document(self):
        res = super()._get_source_document()
        return res or self.production_id or self.raw_material_production_id

    def _get_upstream_documents_and_responsibles(self, visited):
        if self.production_id and self.production_id.state not in ('done', 'cancel'):
            return [(self.production_id, self.production_id.user_id, visited)]
        else:
            return super(StockMove, self)._get_upstream_documents_and_responsibles(visited)

    def _delay_alert_get_documents(self):
        res = super(StockMove, self)._delay_alert_get_documents()
        productions = self.raw_material_production_id | self.production_id
        return res + list(productions)

    def _should_be_assigned(self):
        res = super(StockMove, self)._should_be_assigned()
        return bool(res and not (self.production_id or self.raw_material_production_id))

    def _should_bypass_set_qty_producing(self):
        if self.state in ('done', 'cancel'):
            return True
        # Do not update extra product quantities
        if float_is_zero(self.product_uom_qty, precision_rounding=self.product_uom.rounding):
            return True
        return False

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        vals = super()._prepare_move_line_vals(quantity, reserved_quant)
        if self.raw_material_production_id:
            vals['production_id'] = self.raw_material_production_id.id
        if self.production_id.product_tracking == 'lot' and self.product_id == self.production_id.product_id:
            vals['lot_id'] = self.production_id.lot_producing_id.id
        return vals

    def _key_assign_picking(self):
        keys = super(StockMove, self)._key_assign_picking()
        return keys + (self.created_production_id,)

    def _get_moves_to_propagate_date_deadline(self):
        res = super()._get_moves_to_propagate_date_deadline()
        if self.production_id:
            res |= self.production_id.move_finished_ids - self
        return res

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        res = super()._prepare_merge_moves_distinct_fields()
        res += ['created_production_id', 'cost_share']
        if self.bom_line_id and ("phantom" in self.bom_line_id.bom_id.mapped('type')):
            res.append('bom_line_id')
        return res

    @api.model
    def _prepare_merge_negative_moves_excluded_distinct_fields(self):
        return super()._prepare_merge_negative_moves_excluded_distinct_fields() + ['created_production_id']

    def _compute_kit_quantities(self, product_id, kit_qty, kit_bom, filters):
        """ Computes the quantity delivered or received when a kit is sold or purchased.
        A ratio 'qty_processed/qty_needed' is computed for each component, and the lowest one is kept
        to define the kit's quantity delivered or received.
        :param product_id: The kit itself a.k.a. the finished product
        :param kit_qty: The quantity from the order line
        :param kit_bom: The kit's BoM
        :param filters: Dict of lambda expression to define the moves to consider and the ones to ignore
        :return: The quantity delivered or received
        """
        qty_ratios = []
        kit_qty = kit_qty / kit_bom.product_qty
        boms, bom_sub_lines = kit_bom.explode(product_id, kit_qty)

        def get_qty(move):
            if move.picked:
                return move.product_uom._compute_quantity(move.quantity, move.product_id.uom_id, rounding_method='HALF-UP')
            else:
                return move.product_qty

        for bom_line, bom_line_data in bom_sub_lines:
            # skip service since we never deliver them
            if bom_line.product_id.type == 'service':
                continue
            if float_is_zero(bom_line_data['qty'], precision_rounding=bom_line.product_uom_id.rounding):
                # As BoMs allow components with 0 qty, a.k.a. optionnal components, we simply skip those
                # to avoid a division by zero.
                continue
            bom_line_moves = self.filtered(lambda m: m.bom_line_id == bom_line)
            if bom_line_moves:
                # We compute the quantities needed of each components to make one kit.
                # Then, we collect every relevant moves related to a specific component
                # to know how many are considered delivered.
                uom_qty_per_kit = bom_line_data['qty'] / (bom_line_data['original_qty'])
                qty_per_kit = bom_line.product_uom_id._compute_quantity(uom_qty_per_kit / kit_bom.product_qty, bom_line.product_id.uom_id, round=False)
                if not qty_per_kit:
                    continue
                incoming_qty = sum(bom_line_moves.filtered(filters['incoming_moves']).mapped(get_qty))
                outgoing_qty = sum(bom_line_moves.filtered(filters['outgoing_moves']).mapped(get_qty))
                qty_processed = incoming_qty - outgoing_qty
                # We compute a ratio to know how many kits we can produce with this quantity of that specific component
                qty_ratios.append(float_round(qty_processed / qty_per_kit, precision_rounding=bom_line.product_id.uom_id.rounding))
            else:
                return 0.0
        if qty_ratios:
            # Now that we have every ratio by components, we keep the lowest one to know how many kits we can produce
            # with the quantities delivered of each component. We use the floor division here because a 'partial kit'
            # doesn't make sense.
            return min(qty_ratios) // 1
        else:
            return 0.0

    def _update_candidate_moves_list(self, candidate_moves_set):
        super()._update_candidate_moves_list(candidate_moves_set)
        for production in self.mapped('raw_material_production_id'):
            candidate_moves_set.add(production.move_raw_ids.filtered(lambda m: m.product_id in self.product_id))
        for production in self.mapped('production_id'):
            candidate_moves_set.add(production.move_finished_ids.filtered(lambda m: m.product_id in self.product_id))
        # this will include sibling pickings as a result of merging MOs
        for picking in self.move_dest_ids.raw_material_production_id.picking_ids:
            candidate_moves_set.add(picking.move_ids)

    def _prepare_procurement_values(self):
        res = super()._prepare_procurement_values()
        res['bom_line_id'] = self.bom_line_id.id
        return res

    def action_open_reference(self):
        res = super().action_open_reference()
        source = self.production_id or self.raw_material_production_id
        if source and source.browse().has_access('read'):
            return {
                'res_model': source._name,
                'type': 'ir.actions.act_window',
                'views': [[False, "form"]],
                'res_id': source.id,
            }
        return res

    def _is_manual_consumption(self):
        self.ensure_one()
        return self._determine_is_manual_consumption(self.bom_line_id)

    @api.model
    def _determine_is_manual_consumption(self, bom_line):
        return bom_line and (bom_line.manual_consumption or bom_line.operation_id)

    def _get_relevant_state_among_moves(self):
        res = super()._get_relevant_state_among_moves()
        if res == 'partially_available'\
                and self.raw_material_production_id\
                and all(move.should_consume_qty and float_compare(move.quantity, move.should_consume_qty, precision_rounding=move.product_uom.rounding) >= 0
                        or (float_compare(move.quantity, move.product_uom_qty, precision_rounding=move.product_uom.rounding) >= 0 or (move.manual_consumption and move.picked))
                        for move in self):
            res = 'assigned'
        return res
