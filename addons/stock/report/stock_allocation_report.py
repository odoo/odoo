from collections import OrderedDict, defaultdict

from odoo import api, models
from odoo.fields import Domain


class StockAllocationReport(models.AbstractModel):
    _name = 'stock.allocation.report'
    _description = "Stock Allocation Report"

    @api.model
    def get_report_data(self, data):
        active_model = data['context'].get('active_model', False)
        active_ids = data['context'].get('active_ids', [])
        return self._get_report_values(active_model, active_ids)

    @api.model
    def _get_report_values(self, res_model, res_ids):
        report_values = {
            'product_lines': [],
            'doc': False,
            'reason': self.env._("Operation not found"),
        }
        if not res_model or not res_ids:
            return report_values
        docs = self._get_docs(res_model, res_ids)
        if docs:
            if not self._check_all_records_are_either_done_or_not(docs):
                doc_type = self._get_docs_type(docs)
                report_values['reason'] = self.env._(
                    "This report cannot be used for done and not done %(doc_type)s at the same time",
                    doc_type=doc_type
                )
                return report_values

            product_lines = self._get_product_lines(docs)
            report_values['product_lines'] = list(product_lines.values())
            doc = docs if len(docs) == 1 else docs[0]
            source = self._get_record_source(doc)
            partner_info = self._get_doc_partner(res_model, doc)
            report_values['doc'] = {
                'id': doc.id,
                'res_model': doc._name,
                'name': doc.name,
                'partner': partner_info,
                'source': source,
            }
        return report_values

    def _get_doc_partner(self, res_model, doc):
        if res_model == 'stock.picking':
            return doc.partner_id
        return False

    def _get_record_source(self, record):
        return False

    @api.model
    def _get_docs(self, res_model, ids):
        if res_model == 'stock.picking':
            return self.env['stock.picking'].search([
                ('id', 'in', ids),
                ('picking_type_code', '!=', 'outgoing'),
                ('state', '!=', 'cancel'),
            ])
        return False

    @api.model
    def _check_all_records_are_either_done_or_not(self, records):
        records_state = records.mapped('state')
        return 'done' not in records_state or len(set(records_state)) == 1

    @api.model
    def _get_docs_type(self, docs):
        return self.env._("transfers")

    def _get_product_lines(self, records):
        moves = self._get_moves(records)
        products = moves.product_id
        product_lines = {}

        # Update incoming product lines' quantities.
        for product, moves in moves.grouped('product_id').items():
            assigned_qty, free_qty = 0, 0
            for move in moves:
                if move.state == 'draft':
                    continue  # Draft quantities can't be allocated.
                if move.move_dest_ids:
                    assigned_qty += move.product_qty
                else:
                    free_qty += move.product_qty

            product_lines[product.id] = {
                'assigned_qty': assigned_qty,
                'code': product.code,
                'free_qty': free_qty,
                'id': product.id,
                'move_ids': moves.ids,
                'name': product.name,
                'display_name': product.display_name,
                'needs': [self._get_out_move_values(move_out) for move_out in moves.move_dest_ids],
                'total_qty': sum(move.product_qty for move in moves),
                'uom': product.uom_id.read(['display_name', 'factor'])[0],
            }

        # Find needs.
        warehouse = records.picking_type_id.warehouse_id
        wh_location_ids = self.env['stock.location']._search([
            ('id', 'child_of', warehouse.view_location_id.id),
            ('usage', '!=', 'supplier'),
        ])

        allowed_states = ['confirmed', 'partially_available', 'waiting']
        if records[0].state == 'done':
            # Only done moves are allowed to be assigned to already reserved moves.
            allowed_states += ['assigned']

        domain = Domain.AND([
            Domain([
                ('state', 'in', allowed_states),
                ('product_qty', '>', 0),
                ('location_id', 'in', wh_location_ids),
                ('move_orig_ids', '=', False),
                ('product_id', 'in', products.ids),
            ]),
            self._get_extra_domain(records)
        ])
        out_moves = self.env['stock.move'].search(
            domain,
            order='priority desc, date, id',
            limit=80  # Set an arbitrary limit of 80 moves to keep thing simple.
        )

        # Records out moves' need on corresponding product line.
        for out_move in out_moves:
            source = out_move._get_source_document()
            if not source:
                continue
            out_values = self._get_out_move_values(out_move)
            product_line = product_lines[out_move.product_id.id]
            product_line['needs'].append(out_values)

        return product_lines

    def _get_moves(self, records):
        if records._name == 'stock.picking':
            return records.move_ids.filtered(
                lambda m: m.product_id.is_storable and m.state != 'cancel'
            )
        return self.env['stock.move']

    def _get_extra_domain(self, records):
        if records._name == 'stock.picking':
            return Domain('picking_id', 'not in', records.ids)
        return Domain([])

    def _get_out_move_values(self, out_move):
        picking = out_move.picking_id
        source = out_move._get_source_document()
        partner_info, picking_info, source_info = False, False, False
        if source and source != picking:
            source_info = {
                'id': source.id,
                'res_model': source._name,
                'display_name': source.display_name,
            }
        if picking:
            picking_info = {
                'id': picking.id,
                'res_model': 'stock.picking',
                'display_name': picking.display_name,
            }
            partner_info = {
                'id': picking.partner_id.id,
                'res_model': 'res.partner',
                'display_name': picking.partner_id.display_name,
            } if picking.partner_id else False
        # To handle different UoM quantities, all qties will be expressed in product's UoM.
        reserved_quantity = out_move.quantity
        if out_move.uom_id != out_move.product_id.uom_id:
            reserved_quantity = out_move.product_id.uom_id._compute_quantity(reserved_quantity, out_move.uom_id)
        return {
            **out_move.read(['date', 'priority', 'state'])[0],
            'favorite': out_move.priority == '1',
            'id': out_move.id,
            'is_reserved': bool(out_move.move_orig_ids),
            'move_orig_ids': out_move.move_orig_ids.ids,
            'partner': partner_info,
            'picking': picking_info,
            'reserved_quantity': reserved_quantity,
            'quantity': out_move.product_qty,
            'source': source_info,
            'uom': out_move.product_id.uom_id.read(['display_name', 'factor'])[0],
        }

    # ACTIONS
    @api.model
    def action_assign(self, src_move_ids, out_move_ids, quantity):
        """Assign the given quantity from source moves to out moves. Can split source
        moves if partially assigned, and can split out moves if partially reserved.

        :param list[int] src_move_ids:
        :param list[int] out_move_ids:
        :param int quantity: The quantity to assign (should match the source moves free quantity.)
        :return: A dictionary with two keys: `in_moves` (ids list) and `out_moves` (object list).
        :rtype: dict
        """
        src_moves = self.env['stock.move'].browse(src_move_ids)
        out_moves = self.env['stock.move'].browse(out_move_ids)
        (src_moves | out_moves).product_id.ensure_one()
        self._check_all_records_are_either_done_or_not(src_moves)
        product_uom = src_moves.product_id.uom_id
        new_moves_vals = []
        new_src_moves = self.env['stock.move']
        out_to_new_out = OrderedDict()
        qty_assigned_by_out_move_id = {}

        # Check if some out moves need to be split (less available quantity than demand).
        for out_move in out_moves:
            if product_uom.compare(quantity, 0) <= 0:
                break  # No more available quantity.
            qty_to_assign = min(quantity, out_move.product_qty)
            qty_assigned_by_out_move_id[out_move.id] = qty_to_assign
            quantity -= qty_to_assign
            # Split the out move if not enough quantity to fullfil its demand.
            if product_uom.compare(out_move.product_qty, qty_to_assign) == 1:
                new_move_vals = out_move._split(qty_to_assign)
                out_move.quantity = min(out_move.quantity, out_move.product_uom_qty)
                if new_move_vals:
                    new_move_vals[0]['reservation_date'] = out_move.reservation_date
                new_moves_vals += new_move_vals
                out_to_new_out[out_move.id] = self.env['stock.move']
        new_outs = self.env['stock.move'].create(new_moves_vals)
        outs_to_process = self.env['stock.move'].browse(qty_assigned_by_out_move_id.keys())
        # Don't do action confirm to avoid creating additional unintentional reservations.
        new_outs.write({'state': 'confirmed'})
        # Map new created out moves with their sibling move.
        for i, k in enumerate(out_to_new_out.keys()):
            out_to_new_out[k] = new_outs[i]

        for src_move in src_moves:
            move_quantity = src_move.product_qty or src_move.uom_id._compute_quantity(
                src_move.quantity,
                product_uom,
                rounding_method='HALF-UP'
            )
            already_assigned_qty = sum(src_move.move_dest_ids.mapped('product_qty'))
            available_quantity = move_quantity - already_assigned_qty
            if product_uom.compare(0, available_quantity) >= 0:
                # Source move is already completely linked => don't count it again.
                continue

            outs_fully_processed = self.env['stock.move']
            for out_move in outs_to_process:
                out_to_process = out_move
                if out_move.id in out_to_new_out:
                    # If the out move was split, we left it untouched and
                    # allocate the quantity to the split part instead.
                    new_out = out_to_new_out[out_move.id]
                    if out_move.packaging_uom_id:
                        # Keep track of the initial packaging (which was lost during the split.)
                        new_out.packaging_uom_id = out_move.packaging_uom_id
                    if src_move.state == 'done':
                        out_move.move_line_ids.move_id = new_out
                    out_to_process = new_out

                linked_qty = min(available_quantity, qty_assigned_by_out_move_id[out_move.id])
                available_quantity -= linked_qty
                if src_move.state == 'done' and linked_qty:
                    if out_move.uom_id != product_uom:
                        linked_qty = out_move.uom_id._compute_quantity(linked_qty, product_uom)
                    qty_assigned_by_out_move_id[out_move.id] -= linked_qty
                elif src_move.state != 'done' and\
                     product_uom.compare(linked_qty, src_move.product_qty) != 0:
                    # Split source move to allocate only needed quantity.
                    original_src_move_uom = self._convert_move_quantity(src_move)
                    new_move_vals = src_move._split(src_move.product_qty - linked_qty)
                    new_move = self.env['stock.move'].create(new_move_vals)
                    if original_src_move_uom:
                        new_move.packaging_uom_id = original_src_move_uom
                    new_move._action_confirm(merge=False)
                    new_src_moves |= new_move
                    # Update source move quantity.
                    src_move.quantity = src_move.product_uom_qty
                self._allocate_moves(src_move, out_to_process)
                out_to_process.quantity = min(out_to_process.quantity, out_to_process.product_uom_qty)
                if qty_assigned_by_out_move_id[out_move.id] == 0:
                    outs_fully_processed += out_move
                if product_uom.compare(0, available_quantity) >= 0:
                    # No more qty to assign from this source: stop looping on out moves.
                    break
            outs_to_process -= outs_fully_processed

        all_out_moves = out_moves | new_outs
        all_out_moves._recompute_state()
        # Always try to auto-assign to prevent other moves from reserving the
        # quant if incoming move is done.
        all_out_moves._action_assign()
        return {
            'in_moves': (src_moves | new_src_moves).ids,
            'out_moves': [self._get_out_move_values(out_move) for out_move in all_out_moves],
        }

    @api.model
    def action_assign_all(self, allocation_list):
        res = defaultdict(lambda: {'in_moves': set(), 'out_moves': []})
        for (src_move_ids, allocation_data) in allocation_list:
            product_id = self.env['stock.move'].browse(src_move_ids).product_id.id
            for (out_move_ids, quantity) in allocation_data:
                updated_data = self.action_assign(src_move_ids, out_move_ids, quantity)
                res[product_id]['in_moves'] = updated_data['in_moves']
                res[product_id]['out_moves'].append(updated_data['out_moves'])
        return res

    @api.model
    def action_unassign(self, src_move_ids, out_move_ids, quantity):
        """Unassign the given quantity from out moves and free the allocated
        quantity to source moves. Try to merge both source and out moves in case
         some of them were split during a previous allocation.

        :param list[int] src_move_ids:
        :param list[int] out_move_ids:
        :param int quantity: The quantity to free.
        :return: A dictionary with three keys: `freed_quantity`, `in_moves` (ids list) and `out_moves` (object list).
        :rtype: dict
        """
        src_moves = self.env['stock.move'].browse(src_move_ids)
        out_moves = self.env['stock.move'].browse(out_move_ids)
        (src_moves | out_moves).product_id.ensure_one()
        self._check_all_records_are_either_done_or_not(src_moves)
        freed_src_moves = self.env['stock.move']
        out_moves_to_merge = self.env['stock.move']
        out_moves_to_return = self.env['stock.move']
        outs_to_process = out_moves
        freed_quantity = 0
        for src_move in src_moves:
            for out_move in outs_to_process:
                if src_move not in out_move.move_orig_ids:
                    continue
                freed_qty = out_move.product_uom_qty
                freed_quantity += freed_qty
                self._unallocate_moves(src_move, out_move)
                out_moves_to_merge |= out_move
                freed_src_moves += src_move

        # Try to merge only free source moves.
        moves_to_merge = src_moves.filtered(lambda mv: not mv.move_dest_ids)
        src_moves -= moves_to_merge
        src_moves += freed_src_moves._merge_moves(merge_into=moves_to_merge)

        # Handle annoying use cases where we need to split the out move:
        # 1. batch reserved + individual picking unreserved
        # 2. moves linked from backorder generation
        for out_move in out_moves:
            qty_still_linked = sum(out_move.move_orig_ids.mapped('product_qty'))
            split_vals = out_move._split(qty_still_linked)
            new_move_vals = len(split_vals) >= 1 and split_vals[0]
            if new_move_vals:
                new_move_vals['procure_method'] = 'make_to_order'
                new_move_vals['reservation_date'] = out_move.reservation_date
                new_out = self.env['stock.move'].create(new_move_vals)
                # Don't do action confirm to avoid creating additional unintentional reservations.
                new_out.write({'state': 'confirmed'})
                out_moves_to_return |= new_out
                out_move.move_line_ids.move_id = new_out
                (out_move | new_out)._compute_quantity()
                if new_out.quantity > new_out.product_qty:
                    # Extra reserved amount goes to no longer linked out.
                    reserved_amount_to_remain = new_out.quantity - new_out.product_qty
                    for move_line_id in new_out.move_line_ids:
                        if reserved_amount_to_remain <= 0:
                            break
                        if move_line_id.quantity_product_uom > reserved_amount_to_remain:
                            new_move_line = move_line_id.copy({'quantity': 0})
                            new_move_line.quantity = out_move.product_id.uom_id._compute_quantity(
                                move_line_id.quantity_product_uom - reserved_amount_to_remain,
                                move_line_id.uom_id,
                                rounding_method='HALF-UP'
                            )
                            move_line_id.quantity -= new_move_line.quantity
                            move_line_id.move_id = out_move
                            break
                        else:
                            move_line_id.move_id = out_move
                            reserved_amount_to_remain -= move_line_id.quantity_product_uom
                    (out_move | new_out)._compute_quantity()
                out_move.move_orig_ids = False
                new_out._recompute_state()

        # Check if out moves can be merged (they can have be split by previous allocation.)
        out_moves_to_return |= out_moves_to_merge._merge_moves()

        return {
            'freed_quantity': freed_quantity,
            'in_moves': src_moves.ids,
            'out_moves': [self._get_out_move_values(out_move) for out_move in out_moves_to_return],
        }

    # MOVES METHODS
    def _allocate_moves(self, in_move, out_move):
        """ Assign out move as the in move's destination (create MTO link) and
        share reference across source documents."""
        allocated_location = in_move.picking_type_id.allocated_location_id
        in_move.move_dest_ids |= out_move
        out_move.procure_method = 'make_to_order'
        if (out_ref := out_move.reference_ids) and (in_source := in_move._get_source_document()):
            in_source._add_reference(out_ref)
        if (in_ref := in_move.reference_ids) and (out_source := out_move._get_source_document()):
            out_source._add_reference(in_ref)

        # If in move is not done yet and an allocated location is defined, update its
        # destination to use the allocated location. Out move's source location will
        # be updated only when the operation is done (see `_apply_allocation`).
        if allocated_location and in_move.state != 'done':
            in_move.location_dest_id = allocated_location._get_putaway_strategy(
                in_move.product_id,
                quantity=in_move.product_qty,
                packaging=in_move.packaging_uom_id
            )
            in_move.move_line_ids.location_dest_id = in_move.location_dest_id

    def _unallocate_moves(self, in_move, out_move):
        """ Unassign out move as the in move's destination (break MTO link) and
        remove shared reference across source documents if any."""
        allocated_location = in_move.picking_type_id.allocated_location_id
        if out_ref := out_move.reference_ids:
            in_move._get_source_document()._remove_reference(out_ref)
        if in_ref := in_move.reference_ids:
            out_move._get_source_document()._remove_reference(in_ref)
        out_move._break_mto_link(in_move)
        if allocated_location and in_move.state != 'done':
            # Reset in move's destination location to the default one.
            default_dest_location = in_move.picking_id.location_dest_id or in_move.picking_type_id.default_location_dest_id
            in_move.location_dest_id = default_dest_location

    def _convert_move_quantity(self, move):
        """ Converts the move's UoM into its product's UoM if needed and returns
        the original move's UoM in case a conversion happened.
        This conversion is important because if we need to split the move and it
        uses different UoM than the product's one, we could end up with decimal value.
        Eg.: Imagine 2 units are allocated to a demand of 1 pack of 6, if we
        keep pack of 6 UoM, will we end with two moves:
            - Allocated 0.33 pack of six (2 units);
            - Remaining demand of 4 units (once split, new move uses product's UoM).
        In the report, the 0.33 pack of six will be converted into units, so 1.98 units instead
        of a clean 2 units...
        This missing 0.02 units will completely destroy the allocable quantity compute.

        :return: move's origin UoM in case it was modified, False if not.
        """
        # TODO: it would be better to have a test than an explanation in the docstring.
        original_uom = False
        product_uom = move.product_id.uom_id
        # If we need to split the move and it uses different UoM than the product's one,
        # we convert its quantity into the product's UoM to avoid messy quantity decimal.
        if move.uom_id != product_uom:
            original_uom = move.uom_id
            move.uom_id = product_uom
            move.product_uom_qty *= original_uom.factor / product_uom.factor
            move.packaging_uom_id = original_uom
        return original_uom
