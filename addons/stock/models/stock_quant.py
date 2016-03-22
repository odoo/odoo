from datetime import datetime

from openerp.osv import fields, osv
from openerp.tools.float_utils import float_compare, float_round
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import SUPERUSER_ID
from openerp.exceptions import UserError


class stock_quant(osv.osv):
    """
    Quants are the smallest unit of stock physical instances
    """
    _name = "stock.quant"
    _description = "Quants"

    def _get_quant_name(self, cr, uid, ids, name, args, context=None):
        """ Forms complete name of location from parent location to child location.
        @return: Dictionary of values
        """
        res = {}
        for q in self.browse(cr, uid, ids, context=context):

            res[q.id] = q.product_id.code or ''
            if q.lot_id:
                res[q.id] = q.lot_id.name
            res[q.id] += ': ' + str(q.qty) + q.product_id.uom_id.name
        return res

    def _calc_inventory_value(self, cr, uid, ids, name, attr, context=None):
        context = dict(context or {})
        res = {}
        uid_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        for quant in self.browse(cr, uid, ids, context=context):
            context.pop('force_company', None)
            if quant.company_id.id != uid_company_id:
                #if the company of the quant is different than the current user company, force the company in the context
                #then re-do a browse to read the property fields for the good company.
                context['force_company'] = quant.company_id.id
                quant = self.browse(cr, uid, quant.id, context=context)
            res[quant.id] = self._get_inventory_value(cr, uid, quant, context=context)
        return res

    def _get_inventory_value(self, cr, uid, quant, context=None):
        return quant.product_id.standard_price * quant.qty

    _columns = {
        'name': fields.function(_get_quant_name, type='char', string='Identifier'),
        'product_id': fields.many2one('product.product', 'Product', required=True, ondelete="restrict", readonly=True, select=True),
        'location_id': fields.many2one('stock.location', 'Location', required=True, ondelete="restrict", readonly=True, select=True, auto_join=True),
        'qty': fields.float('Quantity', required=True, help="Quantity of products in this quant, in the default unit of measure of the product", readonly=True, select=True),
        'product_uom_id': fields.related('product_id', 'uom_id', type='many2one', relation="product.uom", string='Unit of Measure', readonly=True),
        'package_id': fields.many2one('stock.quant.package', string='Package', help="The package containing this quant", readonly=True, select=True),
        'packaging_type_id': fields.related('package_id', 'packaging_id', type='many2one', relation='product.packaging', string='Type of packaging', readonly=True, store=True),
        'reservation_id': fields.many2one('stock.move', 'Reserved for Move', help="The move the quant is reserved for", readonly=True, select=True),
        'lot_id': fields.many2one('stock.production.lot', 'Lot', readonly=True, select=True, ondelete="restrict"),
        'cost': fields.float('Unit Cost'),
        'owner_id': fields.many2one('res.partner', 'Owner', help="This is the owner of the quant", readonly=True, select=True),

        'create_date': fields.datetime('Creation Date', readonly=True),
        'in_date': fields.datetime('Incoming Date', readonly=True, select=True),

        'history_ids': fields.many2many('stock.move', 'stock_quant_move_rel', 'quant_id', 'move_id', 'Moves', help='Moves that operate(d) on this quant', copy=False),
        'company_id': fields.many2one('res.company', 'Company', help="The company to which the quants belong", required=True, readonly=True, select=True),
        'inventory_value': fields.function(_calc_inventory_value, string="Inventory Value", type='float', readonly=True),

        # Used for negative quants to reconcile after compensated by a new positive one
        'propagated_from_id': fields.many2one('stock.quant', 'Linked Quant', help='The negative quant this is coming from', readonly=True, select=True),
        'negative_move_id': fields.many2one('stock.move', 'Move Negative Quant', help='If this is a negative quant, this will be the move that caused this negative quant.', readonly=True),
        'negative_dest_location_id': fields.related('negative_move_id', 'location_dest_id', type='many2one', relation='stock.location', string="Negative Destination Location", readonly=True, 
                                                    help="Technical field used to record the destination location of a move that created a negative quant"),
    }

    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.quant', context=c),
    }

    def init(self, cr):
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('stock_quant_product_location_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX stock_quant_product_location_index ON stock_quant (product_id, location_id, company_id, qty, in_date, reservation_id)')

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        ''' Overwrite the read_group in order to sum the function field 'inventory_value' in group by'''
        res = super(stock_quant, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby, lazy=lazy)
        if 'inventory_value' in fields:
            for line in res:
                if '__domain' in line:
                    lines = self.search(cr, uid, line['__domain'], context=context)
                    inv_value = 0.0
                    for line2 in self.browse(cr, uid, lines, context=context):
                        inv_value += line2.inventory_value
                    line['inventory_value'] = inv_value
        return res

    def action_view_quant_history(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display the history of the quant, which
        mean all the stock moves that lead to this quant creation with this quant quantity.
        '''
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'stock', 'action_move_form2')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context={})[0]

        move_ids = []
        for quant in self.browse(cr, uid, ids, context=context):
            move_ids += [move.id for move in quant.history_ids]

        result['domain'] = "[('id','in',[" + ','.join(map(str, move_ids)) + "])]"
        return result

    def quants_reserve(self, cr, uid, quants, move, link=False, context=None):
        '''This function reserves quants for the given move (and optionally given link). If the total of quantity reserved is enough, the move's state
        is also set to 'assigned'

        :param quants: list of tuple(quant browse record or None, qty to reserve). If None is given as first tuple element, the item will be ignored. Negative quants should not be received as argument
        :param move: browse record
        :param link: browse record (stock.move.operation.link)
        '''
        toreserve = []
        reserved_availability = move.reserved_availability
        #split quants if needed
        for quant, qty in quants:
            if qty <= 0.0 or (quant and quant.qty <= 0.0):
                raise UserError(_('You can not reserve a negative quantity or a negative quant.'))
            if not quant:
                continue
            self._quant_split(cr, uid, quant, qty, context=context)
            toreserve.append(quant.id)
            reserved_availability += quant.qty
        #reserve quants
        if toreserve:
            self.write(cr, SUPERUSER_ID, toreserve, {'reservation_id': move.id}, context=context)
        #check if move'state needs to be set as 'assigned'
        rounding = move.product_id.uom_id.rounding
        if float_compare(reserved_availability, move.product_qty, precision_rounding=rounding) == 0 and move.state in ('confirmed', 'waiting')  :
            self.pool.get('stock.move').write(cr, uid, [move.id], {'state': 'assigned'}, context=context)
        elif float_compare(reserved_availability, 0, precision_rounding=rounding) > 0 and not move.partially_available:
            self.pool.get('stock.move').write(cr, uid, [move.id], {'partially_available': True}, context=context)

    def quants_move(self, cr, uid, quants, move, location_to, location_from=False, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False, entire_pack=False, context=None):
        """Moves all given stock.quant in the given destination location.  Unreserve from current move.
        :param quants: list of tuple(browse record(stock.quant) or None, quantity to move)
        :param move: browse record (stock.move)
        :param location_to: browse record (stock.location) depicting where the quants have to be moved
        :param location_from: optional browse record (stock.location) explaining where the quant has to be taken
                              (may differ from the move source location in case a removal strategy applied).
                              This parameter is only used to pass to _quant_create_from_move if a negative quant must be created
        :param lot_id: ID of the lot that must be set on the quants to move
        :param owner_id: ID of the partner that must own the quants to move
        :param src_package_id: ID of the package that contains the quants to move
        :param dest_package_id: ID of the package that must be set on the moved quant
        """
        if location_to.usage == 'view':
            raise UserError(_('You cannot move to a location of type view %s.') % (location_to.name))

        quants_reconcile = []
        to_move_quants = []
        for quant, qty in quants:
            if not quant:
                #If quant is None, we will create a quant to move (and potentially a negative counterpart too)
                quant = self._quant_create_from_move(cr, uid, qty, move, lot_id=lot_id, owner_id=owner_id, src_package_id=src_package_id, dest_package_id=dest_package_id, force_location_from=location_from, force_location_to=location_to, context=context)
            else:
                self._quant_split(cr, uid, quant, qty, context=context)
                to_move_quants.append(quant)
            quants_reconcile.append(quant)
        if to_move_quants:
            to_recompute_move_ids = [x.reservation_id.id for x in to_move_quants if x.reservation_id and x.reservation_id.id != move.id]
            self._quant_update_from_move(cr, uid, to_move_quants, move, location_to, dest_package_id, lot_id=lot_id, entire_pack=entire_pack, context=context)
            self.pool.get('stock.move').recalculate_move_state(cr, uid, to_recompute_move_ids, context=context)
        if location_to.usage == 'internal':
            # Do manual search for quant to avoid full table scan (order by id)
            cr.execute("""
                SELECT 0 FROM stock_quant, stock_location WHERE product_id = %s AND stock_location.id = stock_quant.location_id AND
                ((stock_location.parent_left >= %s AND stock_location.parent_left < %s) OR stock_location.id = %s) AND qty < 0.0 LIMIT 1
            """, (move.product_id.id, location_to.parent_left, location_to.parent_right, location_to.id))
            if cr.fetchone():
                for quant in quants_reconcile:
                    self._quant_reconcile_negative(cr, uid, quant, move, context=context)

    def _quant_update_from_move(self, cr, uid, quants, move, location_dest_id, dest_package_id, lot_id = False, entire_pack=False, context=None):
        context=context or {}
        vals = {'location_id': location_dest_id.id,
                'history_ids': [(4, move.id)],
                'reservation_id': False}
        if lot_id and any(x.id for x in quants if not x.lot_id.id):
            vals['lot_id'] = lot_id
        if not entire_pack:
            vals.update({'package_id': dest_package_id})
        self.write(cr, SUPERUSER_ID, [q.id for q in quants], vals, context=context)
    # compatibility method
    move_quants_write = _quant_update_from_move

    def quants_get_preferred_domain(self, cr, uid, qty, move, ops=False, lot_id=False, domain=None, preferred_domain_list=[], context=None):
        ''' This function tries to find quants for the given domain and move/ops, by trying to first limit
            the choice on the quants that match the first item of preferred_domain_list as well. But if the qty requested is not reached
            it tries to find the remaining quantity by looping on the preferred_domain_list (tries with the second item and so on).
            Make sure the quants aren't found twice => all the domains of preferred_domain_list should be orthogonal
        '''
        return self.quants_get_reservation(
            cr, uid, qty, move,
            pack_operation_id=ops and ops.id or False,
            lot_id=lot_id,
            company_id=context and context.get('company_id', False) or False,
            domain=domain,
            preferred_domain_list=preferred_domain_list,
            context=None)

    def quants_get_reservation(self, cr, uid, qty, move, pack_operation_id=False, lot_id=False, company_id=False, domain=None, preferred_domain_list=None, context=None):
        ''' This function tries to find quants for the given domain and move/ops, by trying to first limit
            the choice on the quants that match the first item of preferred_domain_list as well. But if the qty requested is not reached
            it tries to find the remaining quantity by looping on the preferred_domain_list (tries with the second item and so on).
            Make sure the quants aren't found twice => all the domains of preferred_domain_list should be orthogonal
        '''
        # reserved_quants = []
        reservations = [(None, qty)]
        context = context if context is not None else {}

        pack_operation = self.pool['stock.pack.operation'].browse(cr, uid, pack_operation_id, context=context)
        location = pack_operation.location_id if pack_operation else move.location_id

        if location.usage in ['inventory', 'production', 'supplier']:
            return reservations
            # return self._Reservation(reserved_quants, qty, qty, move, None)

        restrict_lot_id = lot_id if pack_operation else move.restrict_lot_id.id
        removal_strategy = move.get_removal_strategy()

        domain = self._quants_get_reservation_domain(
            cr, uid, move.id,
            pack_operation_id=pack_operation_id,
            lot_id=lot_id,
            company_id=company_id,
            initial_domain=domain,
            context=context)

        if not restrict_lot_id and not preferred_domain_list:
            meta_domains = [[]]
        elif restrict_lot_id and not preferred_domain_list:
            meta_domains = [[('lot_id', '=', restrict_lot_id)], [('lot_id', '=', False)]]
        elif restrict_lot_id and preferred_domain_list:
            lot_list = []
            no_lot_list = []
            for inner_domain in preferred_domain_list:
                lot_list.append(inner_domain + [('lot_id', '=', restrict_lot_id)])
                no_lot_list.append(inner_domain + [('lot_id', '=', False)])
            meta_domains = lot_list + no_lot_list
        else:
            meta_domains = preferred_domain_list

        res_qty = qty
        while (float_compare(res_qty, 0, precision_rounding=move.product_id.uom_id.rounding) and meta_domains):
            additional_domain = meta_domains.pop(0)
            reservations.pop()
            new_reservations = self._quants_get_reservation(
                cr, uid, res_qty, move,
                ops=pack_operation,
                domain=domain + additional_domain,
                removal_strategy=removal_strategy,
                context=context)
            for quant in new_reservations:
                if quant[0]:
                    res_qty -= quant[1]
            reservations += new_reservations

        return reservations

    def _quants_get_reservation_domain(self, cr, uid, move_id, pack_operation_id=False, lot_id=False, company_id=False, initial_domain=None, context=None):
        move = self.pool['stock.move'].browse(cr, uid, move_id, context=context)
        initial_domain = initial_domain if initial_domain is not None else [('qty', '>', 0.0)]
        domain = initial_domain + [('product_id', '=', move.product_id.id)]

        if pack_operation_id:
            pack_operation = self.pool['stock.pack.operation'].browse(cr, uid, pack_operation_id, context=context)
            domain += [('owner_id', '=', pack_operation.owner_id.id), ('location_id', '=', pack_operation.location_id.id)]
            if pack_operation.package_id and not pack_operation.product_id:
                domain += [('package_id', 'child_of', pack_operation.package_id.id)]
            elif pack_operation.package_id and pack_operation.product_id:
                domain += [('package_id', '=', pack_operation.package_id.id)]
            else:
                domain += [('package_id', '=', False)]
        else:
            domain += [('owner_id', '=', move.restrict_partner_id.id), ('location_id', 'child_of', move.location_id.id)]

        if company_id:
            domain += [('company_id', '=', company_id)]
        else:
            domain += [('company_id', '=', move.company_id.id)]

        return domain

    def _quants_removal_get_order(self, cr, uid, removal_strategy=None, context=None):
        if removal_strategy == 'fifo':
            return 'in_date, id'
        elif removal_strategy == 'lifo':
            return 'in_date desc, id desc'
        raise UserError(_('Removal strategy %s not implemented.') % (removal_strategy,))

    def _quants_get_reservation(self, cr, uid, quantity, move, ops=False, domain=None, orderby=None, removal_strategy=None, context=None):
        ''' Implementation of removal strategies.

        :return: a structure containing an ordered list of tuples: quants and
                 the quantity to remove from them. A tuple (None, qty)
                 represents a qty not possible to reserve.
        '''
        if removal_strategy:
            order = self._quants_removal_get_order(cr, uid, removal_strategy, context=context)
        elif orderby:
            order = orderby
        else:
            order = 'in_date'
        rounding = move.product_id.uom_id.rounding
        domain = domain if domain is not None else [('qty', '>', 0.0)]
        res = []
        offset = 0

        remaining_quantity = quantity
        quant_ids = self.search(cr, uid, domain, order=order, limit=10, offset=offset, context=context)
        while float_compare(remaining_quantity, 0, precision_rounding=rounding) > 0 and quant_ids:
            for quant in self.browse(cr, uid, quant_ids, context=context):
                if float_compare(remaining_quantity, abs(quant.qty), precision_rounding=rounding) >= 0:
                    # reserved_quants.append(self._ReservedQuant(quant, abs(quant.qty)))
                    res += [(quant, abs(quant.qty))]
                    remaining_quantity -= abs(quant.qty)
                elif float_compare(remaining_quantity, 0.0, precision_rounding=rounding) != 0:
                    # reserved_quants.append(self._ReservedQuant(quant, remaining_quantity))
                    res += [(quant, remaining_quantity)]
                    remaining_quantity = 0
            offset += 10
            quant_ids = self.search(cr, uid, domain, order=order, limit=10, offset=offset, context=context)

        if float_compare(remaining_quantity, 0, precision_rounding=rounding) > 0:
            res.append((None, remaining_quantity))

        return res

    def _quant_create_from_move(self, cr, uid, qty, move, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False,
                      force_location_from=False, force_location_to=False, context=None):
        '''Create a quant in the destination location and create a negative quant in the source location if it's an internal location.
        '''
        if context is None:
            context = {}
        price_unit = move.get_price_unit()
        location = force_location_to or move.location_dest_id
        rounding = move.product_id.uom_id.rounding
        vals = {
            'product_id': move.product_id.id,
            'location_id': location.id,
            'qty': float_round(qty, precision_rounding=rounding),
            'cost': price_unit,
            'history_ids': [(4, move.id)],
            'in_date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'company_id': move.company_id.id,
            'lot_id': lot_id,
            'owner_id': owner_id,
            'package_id': dest_package_id,
        }
        if move.location_id.usage == 'internal':
            #if we were trying to move something from an internal location and reach here (quant creation),
            #it means that a negative quant has to be created as well.
            negative_vals = vals.copy()
            negative_vals['location_id'] = force_location_from and force_location_from.id or move.location_id.id
            negative_vals['qty'] = float_round(-qty, precision_rounding=rounding)
            negative_vals['cost'] = price_unit
            negative_vals['negative_move_id'] = move.id
            negative_vals['package_id'] = src_package_id
            negative_quant_id = self.create(cr, SUPERUSER_ID, negative_vals, context=context)
            vals.update({'propagated_from_id': negative_quant_id})

        # In case of serial tracking, check if the product does not exist somewhere internally already
        picking_type = move.picking_id and move.picking_id.picking_type_id or False
        if lot_id and move.product_id.tracking == 'serial' and (not picking_type or (picking_type.use_create_lots or picking_type.use_existing_lots)):
            if qty != 1.0:
                raise UserError(_('You should only receive by the piece with the same serial number'))
            other_quants = self.search(cr, uid, [('product_id', '=', move.product_id.id), ('lot_id', '=', lot_id),
                                                 ('qty', '>', 0.0), ('location_id.usage', '=', 'internal')], context=context)
            if other_quants:
                lot_name = self.pool['stock.production.lot'].browse(cr, uid, lot_id, context=context).name
                raise UserError(_('The serial number %s is already in stock.') % lot_name + _("Otherwise make sure the right stock/owner is set."))

        #create the quant as superuser, because we want to restrict the creation of quant manually: we should always use this method to create quants
        quant_id = self.create(cr, SUPERUSER_ID, vals, context=context)
        return self.browse(cr, uid, quant_id, context=context)
    # compatibility method
    _quant_create = _quant_create_from_move

    def _quant_split(self, cr, uid, quant, qty, context=None):
        context = context or {}
        rounding = quant.product_id.uom_id.rounding
        if float_compare(abs(quant.qty), abs(qty), precision_rounding=rounding) <= 0: # if quant <= qty in abs, take it entirely
            return False
        qty_round = float_round(qty, precision_rounding=rounding)
        new_qty_round = float_round(quant.qty - qty, precision_rounding=rounding)
        # Fetch the history_ids manually as it will not do a join with the stock moves then (=> a lot faster)
        cr.execute("""SELECT move_id FROM stock_quant_move_rel WHERE quant_id = %s""", (quant.id,))
        res = cr.fetchall()
        new_quant = self.copy(cr, SUPERUSER_ID, quant.id, default={'qty': new_qty_round, 'history_ids': [(4, x[0]) for x in res]}, context=context)
        self.write(cr, SUPERUSER_ID, quant.id, {'qty': qty_round}, context=context)
        return self.browse(cr, uid, new_quant, context=context)

    def _get_latest_move(self, cr, uid, quant, context=None):
        move = False
        for m in quant.history_ids:
            if not move or m.date > move.date:
                move = m
        return move

    def _search_quants_to_reconcile(self, cr, uid, quant, context=None):
        """
            Searches negative quants to reconcile for where the quant to reconcile is put
        """
        dom = [('qty', '<', 0)]
        order = 'in_date'
        dom += [('location_id', 'child_of', quant.location_id.id), ('product_id', '=', quant.product_id.id),
                ('owner_id', '=', quant.owner_id.id)]
        if quant.package_id.id:
            dom += [('package_id', '=', quant.package_id.id)]
        if quant.lot_id:
            dom += ['|', ('lot_id', '=', False), ('lot_id', '=', quant.lot_id.id)]
            order = 'lot_id, in_date'
        # Do not let the quant eat itself, or it will kill its history (e.g. returns / Stock -> Stock)
        dom += [('id', '!=', quant.propagated_from_id.id)]
        quants_search = self.search(cr, uid, dom, order=order, context=context)
        product = quant.product_id
        quants = []
        quantity = quant.qty
        for quant in self.browse(cr, uid, quants_search, context=context):
            rounding = product.uom_id.rounding
            if float_compare(quantity, abs(quant.qty), precision_rounding=rounding) >= 0:
                quants += [(quant, abs(quant.qty))]
                quantity -= abs(quant.qty)
            elif float_compare(quantity, 0.0, precision_rounding=rounding) != 0:
                quants += [(quant, quantity)]
                quantity = 0
                break
        return quants

    def _quant_reconcile_negative(self, cr, uid, quant, move, context=None):
        """
            When new quant arrive in a location, try to reconcile it with
            negative quants. If it's possible, apply the cost of the new
            quant to the counterpart of the negative quant.
        """
        context = context or {}
        context = dict(context)
        context.update({'force_unlink': True})
        solving_quant = quant
        quants = self._search_quants_to_reconcile(cr, uid, quant, context=context)
        product_uom_rounding = quant.product_id.uom_id.rounding
        for quant_neg, qty in quants:
            if not quant_neg or not solving_quant:
                continue
            to_solve_quant_ids = self.search(cr, uid, [('propagated_from_id', '=', quant_neg.id)], context=context)
            if not to_solve_quant_ids:
                continue
            solving_qty = qty
            solved_quant_ids = []
            for to_solve_quant in self.browse(cr, uid, to_solve_quant_ids, context=context):
                if float_compare(solving_qty, 0, precision_rounding=product_uom_rounding) <= 0:
                    continue
                solved_quant_ids.append(to_solve_quant.id)
                self._quant_split(cr, uid, to_solve_quant, min(solving_qty, to_solve_quant.qty), context=context)
                solving_qty -= min(solving_qty, to_solve_quant.qty)
            remaining_solving_quant = self._quant_split(cr, uid, solving_quant, qty, context=context)
            remaining_neg_quant = self._quant_split(cr, uid, quant_neg, -qty, context=context)
            #if the reconciliation was not complete, we need to link together the remaining parts
            if remaining_neg_quant:
                remaining_to_solve_quant_ids = self.search(cr, uid, [('propagated_from_id', '=', quant_neg.id), ('id', 'not in', solved_quant_ids)], context=context)
                if remaining_to_solve_quant_ids:
                    self.write(cr, SUPERUSER_ID, remaining_to_solve_quant_ids, {'propagated_from_id': remaining_neg_quant.id}, context=context)
            if solving_quant.propagated_from_id and solved_quant_ids:
                self.write(cr, SUPERUSER_ID, solved_quant_ids, {'propagated_from_id': solving_quant.propagated_from_id.id}, context=context)
            #delete the reconciled quants, as it is replaced by the solved quants
            self.unlink(cr, SUPERUSER_ID, [quant_neg.id], context=context)
            if solved_quant_ids:
                #price update + accounting entries adjustments
                self._price_update(cr, uid, solved_quant_ids, solving_quant.cost, context=context)
                #merge history (and cost?)
                self.write(
                    cr, SUPERUSER_ID, solved_quant_ids, {
                        'history_ids': [(4, history_move.id) for history_move in solving_quant.history_ids]
                    }, context=context)
            self.unlink(cr, SUPERUSER_ID, [solving_quant.id], context=context)
            solving_quant = remaining_solving_quant

    def _price_update(self, cr, uid, ids, newprice, context=None):
        self.write(cr, SUPERUSER_ID, ids, {'cost': newprice}, context=context)

    def unlink(self, cr, uid, ids, context=None):
        context = context or {}
        if not context.get('force_unlink'):
            raise UserError(_('Under no circumstances should you delete or change quants yourselves!'))
        super(stock_quant, self).unlink(cr, uid, ids, context=context)


class stock_package(osv.osv):
    """
    These are the packages, containing quants and/or other packages
    """
    _name = "stock.quant.package"
    _description = "Physical Packages"
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'name'
    _order = 'parent_left'

    def name_get(self, cr, uid, ids, context=None):
        res = self._complete_name(cr, uid, ids, 'complete_name', None, context=context)
        return res.items()

    def _complete_name(self, cr, uid, ids, name, args, context=None):
        """ Forms complete name of location from parent location to child location.
        @return: Dictionary of values
        """
        res = {}
        for m in self.browse(cr, uid, ids, context=context):
            res[m.id] = m.name
            parent = m.parent_id
            while parent:
                res[m.id] = parent.name + ' / ' + res[m.id]
                parent = parent.parent_id
        return res

    def _get_packages(self, cr, uid, ids, context=None):
        """Returns packages from quants for store"""
        res = set()
        for quant in self.browse(cr, uid, ids, context=context):
            pack = quant.package_id
            while pack:
                res.add(pack.id)
                pack = pack.parent_id
        return list(res)

    def _get_package_info(self, cr, uid, ids, name, args, context=None):
        quant_obj = self.pool.get("stock.quant")
        default_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        res = dict((res_id, {'location_id': False, 'company_id': default_company_id, 'owner_id': False}) for res_id in ids)
        for pack in self.browse(cr, uid, ids, context=context):
            quants = quant_obj.search(cr, uid, [('package_id', 'child_of', pack.id)], context=context)
            if quants:
                quant = quant_obj.browse(cr, uid, quants[0], context=context)
                res[pack.id]['location_id'] = quant.location_id.id
                res[pack.id]['owner_id'] = quant.owner_id.id
                res[pack.id]['company_id'] = quant.company_id.id
            else:
                res[pack.id]['location_id'] = False
                res[pack.id]['owner_id'] = False
                res[pack.id]['company_id'] = False
        return res

    def _get_packages_to_relocate(self, cr, uid, ids, context=None):
        res = set()
        for pack in self.browse(cr, uid, ids, context=context):
            res.add(pack.id)
            if pack.parent_id:
                res.add(pack.parent_id.id)
        return list(res)

    _columns = {
        'name': fields.char('Package Reference', select=True, copy=False),
        'parent_left': fields.integer('Left Parent', select=1),
        'parent_right': fields.integer('Right Parent', select=1),
        'packaging_id': fields.many2one('product.packaging', 'Package Type', help="This field should be completed only if everything inside the package share the same product, otherwise it doesn't really makes sense.", select=True),
        'location_id': fields.function(_get_package_info, type='many2one', relation='stock.location', string='Location', multi="package",
                                    store={
                                       'stock.quant': (_get_packages, ['location_id'], 10),
                                       'stock.quant.package': (_get_packages_to_relocate, ['quant_ids', 'children_ids', 'parent_id'], 10),
                                    }, readonly=True, select=True),
        'quant_ids': fields.one2many('stock.quant', 'package_id', 'Bulk Content', readonly=True),
        'parent_id': fields.many2one('stock.quant.package', 'Parent Package', help="The package containing this item", ondelete='restrict', readonly=True),
        'children_ids': fields.one2many('stock.quant.package', 'parent_id', 'Contained Packages', readonly=True),
        'company_id': fields.function(_get_package_info, type="many2one", relation='res.company', string='Company', multi="package", 
                                    store={
                                       'stock.quant': (_get_packages, ['company_id'], 10),
                                       'stock.quant.package': (_get_packages_to_relocate, ['quant_ids', 'children_ids', 'parent_id'], 10),
                                    }, readonly=True, select=True),
        'owner_id': fields.function(_get_package_info, type='many2one', relation='res.partner', string='Owner', multi="package",
                                store={
                                       'stock.quant': (_get_packages, ['owner_id'], 10),
                                       'stock.quant.package': (_get_packages_to_relocate, ['quant_ids', 'children_ids', 'parent_id'], 10),
                                    }, readonly=True, select=True),
    }
    _defaults = {
        'name': lambda self, cr, uid, context: self.pool.get('ir.sequence').next_by_code(cr, uid, 'stock.quant.package') or _('Unknown Pack')
    }

    def _check_location_constraint(self, cr, uid, ids, context=None):
        '''checks that all quants in a package are stored in the same location. This function cannot be used
           as a constraint because it needs to be checked on pack operations (they may not call write on the
           package)
        '''
        packs = self.browse(cr, uid, ids, context=context)
        quant_obj = self.pool.get('stock.quant')
        for pack in packs:
            parent = pack
            while parent.parent_id:
                parent = parent.parent_id
            quant_ids = self.get_content(cr, uid, [parent.id], context=context)
            quants = [x for x in quant_obj.browse(cr, uid, quant_ids, context=context) if x.qty > 0]
            location_id = quants and quants[0].location_id.id or False
            if not [quant.location_id.id == location_id for quant in quants]:
                raise UserError(_('Everything inside a package should be in the same location'))
        return True

    def unpack(self, cr, uid, ids, context=None):
        quant_obj = self.pool.get('stock.quant')
        for package in self.browse(cr, uid, ids, context=context):
            quant_ids = [quant.id for quant in package.quant_ids]
            quant_obj.write(cr, SUPERUSER_ID, quant_ids, {'package_id': package.parent_id.id or False}, context=context)
            children_package_ids = [child_package.id for child_package in package.children_ids]
            self.write(cr, uid, children_package_ids, {'parent_id': package.parent_id.id or False}, context=context)
        #delete current package since it contains nothing anymore
        self.unlink(cr, uid, ids, context=context)
        return self.pool.get('ir.actions.act_window').for_xml_id(cr, uid, 'stock', 'action_package_view', context=context)

    def get_content(self, cr, uid, ids, context=None):
        child_package_ids = self.search(cr, uid, [('id', 'child_of', ids)], context=context)
        return self.pool.get('stock.quant').search(cr, uid, [('package_id', 'in', child_package_ids)], context=context)

    def get_content_package(self, cr, uid, ids, context=None):
        quants_ids = self.get_content(cr, uid, ids, context=context)
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid, 'stock', 'quantsact', context=context)
        res['domain'] = [('id', 'in', quants_ids)]
        return res

    def _get_all_products_quantities(self, cr, uid, ids, context=None):
        '''This function computes the different product quantities for the given package
        '''
        quant_obj = self.pool.get('stock.quant')
        res = {}
        for quant in quant_obj.browse(cr, uid, self.get_content(cr, uid, ids, context=context)):
            if quant.product_id not in res:
                res[quant.product_id] = 0
            res[quant.product_id] += quant.qty
        return res
