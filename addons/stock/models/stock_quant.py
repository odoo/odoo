from datetime import datetime

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare, float_round
from odoo.tools.translate import _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class Quant(models.Model):
    """ Quants are the smallest unit of stock physical instances """
    _name = "stock.quant"
    _description = "Quants"

    name = fields.Char(string='Identifier', compute='_compute_name')
    product_id = fields.Many2one(
        'product.product', 'Product',
        index=True, ondelete="restrict", readonly=True, required=True)
    location_id = fields.Many2one(
        'stock.location', 'Location',
        auto_join=True, index=True, ondelete="restrict", readonly=True, required=True)
    qty = fields.Float(
        'Quantity',
        index=True, readonly=True, required=True,
        help="Quantity of products in this quant, in the default unit of measure of the product")
    product_uom_id = fields.Many2one(
        'product.uom', string='Unit of Measure', related='product_id.uom_id',
        readonly=True)
    package_id = fields.Many2one(
        'stock.quant.package', string='Package',
        index=True, readonly=True,
        help="The package containing this quant")
    packaging_type_id = fields.Many2one(
        'product.packaging', string='Type of packaging', related='package_id.packaging_id',
        readonly=True, store=True)
    reservation_id = fields.Many2one(
        'stock.move', 'Reserved for Move',
        index=True, readonly=True,
        help="The move the quant is reserved for")
    lot_id = fields.Many2one(
        'stock.production.lot', 'Lot/Serial Number',
        index=True, ondelete="restrict", readonly=True)
    cost = fields.Float('Unit Cost', group_operator='avg')
    owner_id = fields.Many2one(
        'res.partner', 'Owner',
        index=True, readonly=True,
        help="This is the owner of the quant")
    create_date = fields.Datetime('Creation Date', readonly=True)
    in_date = fields.Datetime('Incoming Date', index=True, readonly=True)
    history_ids = fields.Many2many(
        'stock.move', 'stock_quant_move_rel', 'quant_id', 'move_id',
        string='Moves', copy=False,
        help='Moves that operate(d) on this quant')
    company_id = fields.Many2one(
        'res.company', 'Company',
        index=True, readonly=True, required=True,
        default=lambda self: self.env['res.company']._company_default_get('stock.quant'),
        help="The company to which the quants belong")
    inventory_value = fields.Float('Inventory Value', compute='_compute_inventory_value', readonly=True)
    # Used for negative quants to reconcile after compensated by a new positive one
    propagated_from_id = fields.Many2one(
        'stock.quant', 'Linked Quant',
        index=True, readonly=True,
        help='The negative quant this is coming from')
    negative_move_id = fields.Many2one(
        'stock.move', 'Move Negative Quant',
        readonly=True,
        help='If this is a negative quant, this will be the move that caused this negative quant.')
    negative_dest_location_id = fields.Many2one(
        'stock.location', "Negative Destination Location", related='negative_move_id.location_dest_id',
        readonly=True,
        help="Technical field used to record the destination location of a move that created a negative quant")

    @api.one
    def _compute_name(self):
        """ Forms complete name of location from parent location to child location. """
        self.name = '%s: %s%s' % (self.lot_id.name or self.product_id.code or '', self.qty, self.product_id.uom_id.name)

    @api.multi
    def _compute_inventory_value(self):
        for quant in self:
            if quant.company_id != self.env.user.company_id:
                # if the company of the quant is different than the current user company, force the company in the context
                # then re-do a browse to read the property fields for the good company.
                quant = quant.with_context(force_company=quant.company_id.id)
            quant.inventory_value = quant.product_id.standard_price * quant.qty

    @api.model_cr
    def init(self):
        self._cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('stock_quant_product_location_index',))
        if not self._cr.fetchone():
            self._cr.execute('CREATE INDEX stock_quant_product_location_index ON stock_quant (product_id, location_id, company_id, qty, in_date, reservation_id)')

    @api.multi
    def unlink(self):
        # TDE FIXME: should probably limitate unlink to admin and sudo calls to unlink, because context is not safe
        if not self.env.context.get('force_unlink'):
            raise UserError(_('Under no circumstances should you delete or change quants yourselves!'))
        return super(Quant, self).unlink()

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        " Overwrite the read_group in order to sum the function field 'inventory_value' in group by "
        # TDE NOTE: WHAAAAT ??? is this because inventory_value is not stored ?
        # TDE FIXME: why not storing the inventory_value field ? company_id is required, stored, and should not create issues
        res = super(Quant, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        if 'inventory_value' in fields:
            for line in res:
                if '__domain' in line:
                    lines = self.search(line['__domain'])
                    inv_value = 0.0
                    for line2 in lines:
                        inv_value += line2.inventory_value
                    line['inventory_value'] = inv_value
        return res

    @api.multi
    def action_view_quant_history(self):
        ''' Returns an action that display the history of the quant, which
        mean all the stock moves that lead to this quant creation with this
        quant quantity. '''
        action = self.env.ref('stock', 'stock_move_action').read()[0]
        action['domain'] = [('id', 'in', self.mapped('history_ids').ids)]
        return action

    @api.model
    def quants_reserve(self, quants, move, link=False):
        ''' This function reserves quants for the given move and optionally
        given link. If the total of quantity reserved is enough, the move state
        is also set to 'assigned'

        :param quants: list of tuple(quant browse record or None, qty to reserve). If None is given as first tuple element, the item will be ignored. Negative quants should not be received as argument
        :param move: browse record
        :param link: browse record (stock.move.operation.link)
        '''
        # TDE CLEANME: use ids + quantities dict
        # TDE CLEANME: check use of sudo
        quants_to_reserve_sudo = self.env['stock.quant'].sudo()
        reserved_availability = move.reserved_availability
        # split quants if needed
        for quant, qty in quants:
            if qty <= 0.0 or (quant and quant.qty <= 0.0):
                raise UserError(_('You can not reserve a negative quantity or a negative quant.'))
            if not quant:
                continue
            quant._quant_split(qty)
            quants_to_reserve_sudo |= quant
            reserved_availability += quant.qty
        # reserve quants
        if quants_to_reserve_sudo:
            quants_to_reserve_sudo.write({'reservation_id': move.id})
        # check if move state needs to be set as 'assigned'
        # TDE CLEANME: should be moved as a move model method IMO
        rounding = move.product_id.uom_id.rounding
        if float_compare(reserved_availability, move.product_qty, precision_rounding=rounding) == 0 and move.state in ('confirmed', 'waiting'):
            move.write({'state': 'assigned'})
        elif float_compare(reserved_availability, 0, precision_rounding=rounding) > 0 and not move.partially_available:
            move.write({'partially_available': True})

    @api.model
    def quants_move(self, quants, move, location_to, location_from=False, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False, entire_pack=False):
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
        # TDE CLEANME: use ids + quantities dict
        if location_to.usage == 'view':
            raise UserError(_('You cannot move to a location of type view %s.') % (location_to.name))

        quants_reconcile_sudo = self.env['stock.quant'].sudo()
        quants_move_sudo = self.env['stock.quant'].sudo()
        check_lot = False
        for quant, qty in quants:
            if not quant:
                #If quant is None, we will create a quant to move (and potentially a negative counterpart too)
                quant = self._quant_create_from_move(
                    qty, move, lot_id=lot_id, owner_id=owner_id, src_package_id=src_package_id, dest_package_id=dest_package_id, force_location_from=location_from, force_location_to=location_to)
                check_lot = True
            else:
                quant._quant_split(qty)
                quants_move_sudo |= quant
            quants_reconcile_sudo |= quant

        if quants_move_sudo:
            moves_recompute = quants_move_sudo.filtered(lambda self: self.reservation_id != move).mapped('reservation_id')
            quants_move_sudo._quant_update_from_move(move, location_to, dest_package_id, lot_id=lot_id, entire_pack=entire_pack)
            moves_recompute.recalculate_move_state()

        if location_to.usage == 'internal':
            # Do manual search for quant to avoid full table scan (order by id)
            self._cr.execute("""
                SELECT 0 FROM stock_quant, stock_location WHERE product_id = %s AND stock_location.id = stock_quant.location_id AND
                ((stock_location.parent_left >= %s AND stock_location.parent_left < %s) OR stock_location.id = %s) AND qty < 0.0 LIMIT 1
            """, (move.product_id.id, location_to.parent_left, location_to.parent_right, location_to.id))
            if self._cr.fetchone():
                quants_reconcile_sudo._quant_reconcile_negative(move)

        # In case of serial tracking, check if the product does not exist somewhere internally already
        # Checking that a positive quant already exists in an internal location is too restrictive.
        # Indeed, if a warehouse is configured with several steps (e.g. "Pick + Pack + Ship") and
        # one step is forced (creates a quant of qty = -1.0), it is not possible afterwards to
        # correct the inventory unless the product leaves the stock.
        picking_type = move.picking_id and move.picking_id.picking_type_id or False
        if check_lot and lot_id and move.product_id.tracking == 'serial' and (not picking_type or (picking_type.use_create_lots or picking_type.use_existing_lots)):
            other_quants = self.search([('product_id', '=', move.product_id.id), ('lot_id', '=', lot_id),
                                        ('qty', '>', 0.0), ('location_id.usage', '=', 'internal')])
            if other_quants:
                # We raise an error if:
                # - the total quantity is strictly larger than 1.0
                # - there are more than one negative quant, to avoid situations where the user would
                #   force the quantity at several steps of the process
                if sum(other_quants.mapped('qty')) > 1.0 or len([q for q in other_quants.mapped('qty') if q < 0]) > 1:
                    lot_name = self.env['stock.production.lot'].browse(lot_id).name
                    raise UserError(_('The serial number %s is already in stock.') % lot_name + _("Otherwise make sure the right stock/owner is set."))

    @api.model
    def _quant_create_from_move(self, qty, move, lot_id=False, owner_id=False,
                                src_package_id=False, dest_package_id=False,
                                force_location_from=False, force_location_to=False):
        '''Create a quant in the destination location and create a negative
        quant in the source location if it's an internal location. '''
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
            # if we were trying to move something from an internal location and reach here (quant creation),
            # it means that a negative quant has to be created as well.
            negative_vals = vals.copy()
            negative_vals['location_id'] = force_location_from and force_location_from.id or move.location_id.id
            negative_vals['qty'] = float_round(-qty, precision_rounding=rounding)
            negative_vals['cost'] = price_unit
            negative_vals['negative_move_id'] = move.id
            negative_vals['package_id'] = src_package_id
            negative_quant_id = self.sudo().create(negative_vals)
            vals.update({'propagated_from_id': negative_quant_id.id})

        picking_type = move.picking_id and move.picking_id.picking_type_id or False
        if lot_id and move.product_id.tracking == 'serial' and (not picking_type or (picking_type.use_create_lots or picking_type.use_existing_lots)):
            if qty != 1.0:
                raise UserError(_('You should only receive by the piece with the same serial number'))

        # create the quant as superuser, because we want to restrict the creation of quant manually: we should always use this method to create quants
        return self.sudo().create(vals)

    @api.model
    def _quant_create(self, qty, move, lot_id=False, owner_id=False,
                      src_package_id=False, dest_package_id=False,
                      force_location_from=False, force_location_to=False):
        # FIXME - remove me in master/saas-14
        _logger.warning("'_quant_create' has been renamed into '_quant_create_from_move'... Overrides are ignored")
        return self._quant_create_from_move(
            qty, move, lot_id=lot_id, owner_id=owner_id,
            src_package_id=src_package_id, dest_package_id=dest_package_id,
            force_location_from=force_location_from, force_location_to=force_location_to)

    @api.multi
    def _quant_update_from_move(self, move, location_dest_id, dest_package_id, lot_id=False, entire_pack=False):
        vals = {
            'location_id': location_dest_id.id,
            'history_ids': [(4, move.id)],
            'reservation_id': False}
        if lot_id and any(quant for quant in self if not quant.lot_id.id):
            vals['lot_id'] = lot_id
        if not entire_pack:
            vals.update({'package_id': dest_package_id})
        self.write(vals)

    @api.multi
    def move_quants_write(self, move, location_dest_id, dest_package_id, lot_id=False, entire_pack=False):
        # FIXME - remove me in master/saas-14
        _logger.warning("'move_quants_write' has been renamed into '_quant_update_from_move'... Overrides are ignored")
        return self._quant_update_from_move(move, location_dest_id, dest_package_id, lot_id=lot_id, entire_pack=entire_pack)

    @api.one
    def _quant_reconcile_negative(self, move):
        """
            When new quant arrive in a location, try to reconcile it with
            negative quants. If it's possible, apply the cost of the new
            quant to the counterpart of the negative quant.
        """
        solving_quant = self
        quants = self._search_quants_to_reconcile()
        product_uom_rounding = self.product_id.uom_id.rounding
        for quant_neg, qty in quants:
            if not quant_neg or not solving_quant:
                continue
            quants_to_solve = self.search([('propagated_from_id', '=', quant_neg.id)])
            if not quants_to_solve:
                continue
            solving_qty = qty
            solved_quants = self.env['stock.quant'].sudo()
            for to_solve_quant in quants_to_solve:
                if float_compare(solving_qty, 0, precision_rounding=product_uom_rounding) <= 0:
                    continue
                solved_quants |= to_solve_quant
                to_solve_quant._quant_split(min(solving_qty, to_solve_quant.qty))
                solving_qty -= min(solving_qty, to_solve_quant.qty)
            remaining_solving_quant = solving_quant._quant_split(qty)
            remaining_neg_quant = quant_neg._quant_split(-qty)
            # if the reconciliation was not complete, we need to link together the remaining parts
            if remaining_neg_quant:
                remaining_to_solves = self.sudo().search([('propagated_from_id', '=', quant_neg.id), ('id', 'not in', solved_quants.ids)])
                if remaining_to_solves:
                    remaining_to_solves.write({'propagated_from_id': remaining_neg_quant.id})
            if solving_quant.propagated_from_id and solved_quants:
                solved_quants.write({'propagated_from_id': solving_quant.propagated_from_id.id})
            # delete the reconciled quants, as it is replaced by the solved quants
            quant_neg.sudo().with_context(force_unlink=True).unlink()
            if solved_quants:
                # price update + accounting entries adjustments
                solved_quants._price_update(solving_quant.cost)
                # merge history (and cost?)
                solved_quants.write(solving_quant._prepare_history())
            solving_quant.with_context(force_unlink=True).unlink()
            solving_quant = remaining_solving_quant

    def _prepare_history(self):
        return {
            'history_ids': [(4, history_move.id) for history_move in self.history_ids],
        }

    @api.multi
    def _price_update(self, newprice):
        # TDE note: use ACLs instead of sudoing everything
        self.sudo().write({'cost': newprice})

    @api.multi
    def _search_quants_to_reconcile(self):
        """ Searches negative quants to reconcile for where the quant to reconcile is put """
        dom = ['&', '&', '&', '&',
               ('qty', '<', 0),
               ('location_id', 'child_of', self.location_id.id),
               ('product_id', '=', self.product_id.id),
               ('owner_id', '=', self.owner_id.id),
               # Do not let the quant eat itself, or it will kill its history (e.g. returns / Stock -> Stock)
               ('id', '!=', self.propagated_from_id.id)]
        if self.package_id.id:
            dom = ['&'] + dom + [('package_id', '=', self.package_id.id)]
        if self.lot_id:
            dom = ['&'] + dom + ['|', ('lot_id', '=', False), ('lot_id', '=', self.lot_id.id)]
            order = 'lot_id, in_date'
        else:
            order = 'in_date'

        rounding = self.product_id.uom_id.rounding
        quants = []
        quantity = self.qty
        for quant in self.search(dom, order=order):
            if float_compare(quantity, abs(quant.qty), precision_rounding=rounding) >= 0:
                quants += [(quant, abs(quant.qty))]
                quantity -= abs(quant.qty)
            elif float_compare(quantity, 0.0, precision_rounding=rounding) != 0:
                quants += [(quant, quantity)]
                quantity = 0
                break
        return quants

    @api.model
    def quants_get_preferred_domain(self, qty, move, ops=False, lot_id=False, domain=None, preferred_domain_list=[]):
        ''' This function tries to find quants for the given domain and move/ops, by trying to first limit
            the choice on the quants that match the first item of preferred_domain_list as well. But if the qty requested is not reached
            it tries to find the remaining quantity by looping on the preferred_domain_list (tries with the second item and so on).
            Make sure the quants aren't found twice => all the domains of preferred_domain_list should be orthogonal
        '''
        return self.quants_get_reservation(
            qty, move,
            pack_operation_id=ops and ops.id or False,
            lot_id=lot_id,
            company_id=self.env.context.get('company_id', False),
            domain=domain,
            preferred_domain_list=preferred_domain_list)

    def quants_get_reservation(self, qty, move, pack_operation_id=False, lot_id=False, company_id=False, domain=None, preferred_domain_list=None):
        ''' This function tries to find quants for the given domain and move/ops, by trying to first limit
            the choice on the quants that match the first item of preferred_domain_list as well. But if the qty requested is not reached
            it tries to find the remaining quantity by looping on the preferred_domain_list (tries with the second item and so on).
            Make sure the quants aren't found twice => all the domains of preferred_domain_list should be orthogonal
        '''
        # TDE FIXME: clean me
        reservations = [(None, qty)]

        pack_operation = self.env['stock.pack.operation'].browse(pack_operation_id)
        location = pack_operation.location_id if pack_operation else move.location_id

        # don't look for quants in location that are of type production, supplier or inventory.
        if location.usage in ['inventory', 'production', 'supplier']:
            return reservations
            # return self._Reservation(reserved_quants, qty, qty, move, None)

        restrict_lot_id = lot_id if pack_operation else move.restrict_lot_id.id or lot_id
        removal_strategy = move.get_removal_strategy()

        domain = self._quants_get_reservation_domain(
            move,
            pack_operation_id=pack_operation_id,
            lot_id=lot_id,
            company_id=company_id,
            initial_domain=domain)

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
                res_qty, move,
                ops=pack_operation,
                domain=domain + additional_domain,
                removal_strategy=removal_strategy)
            for quant in new_reservations:
                if quant[0]:
                    res_qty -= quant[1]
            reservations += new_reservations

        return reservations

    def _quants_get_reservation_domain(self, move, pack_operation_id=False, lot_id=False, company_id=False, initial_domain=None):
        initial_domain = initial_domain if initial_domain is not None else [('qty', '>', 0.0)]
        domain = initial_domain + [('product_id', '=', move.product_id.id)]

        if pack_operation_id:
            pack_operation = self.env['stock.pack.operation'].browse(pack_operation_id)
            domain += [('location_id', '=', pack_operation.location_id.id)]
            if pack_operation.owner_id:
                domain += [('owner_id', '=', pack_operation.owner_id.id)]
            if pack_operation.package_id and not pack_operation.product_id:
                domain += [('package_id', 'child_of', pack_operation.package_id.id)]
            elif pack_operation.package_id and pack_operation.product_id:
                domain += [('package_id', '=', pack_operation.package_id.id)]
            else:
                domain += [('package_id', '=', False)]
        else:
            domain += [('location_id', 'child_of', move.location_id.id)]
            if move.restrict_partner_id:
                domain += [('owner_id', '=', move.restrict_partner_id.id)]

        if company_id:
            domain += [('company_id', '=', company_id)]
        else:
            domain += [('company_id', '=', move.company_id.id)]

        return domain

    @api.model
    def _quants_removal_get_order(self, removal_strategy=None):
        if removal_strategy == 'fifo':
            return 'in_date, id'
        elif removal_strategy == 'lifo':
            return 'in_date desc, id desc'
        raise UserError(_('Removal strategy %s not implemented.') % (removal_strategy,))

    def _quants_get_reservation(self, quantity, move, ops=False, domain=None, orderby=None, removal_strategy=None):
        ''' Implementation of removal strategies.

        :return: a structure containing an ordered list of tuples: quants and
                 the quantity to remove from them. A tuple (None, qty)
                 represents a qty not possible to reserve.
        '''
        # TDE FIXME: try to clean
        if removal_strategy:
            order = self._quants_removal_get_order(removal_strategy)
        elif orderby:
            order = orderby
        else:
            order = 'in_date'
        rounding = move.product_id.uom_id.rounding
        domain = domain if domain is not None else [('qty', '>', 0.0)]
        res = []
        offset = 0

        remaining_quantity = quantity
        quants = self.search(domain, order=order, limit=10, offset=offset)
        while float_compare(remaining_quantity, 0, precision_rounding=rounding) > 0 and quants:
            for quant in quants:
                if float_compare(remaining_quantity, abs(quant.qty), precision_rounding=rounding) >= 0:
                    # reserved_quants.append(self._ReservedQuant(quant, abs(quant.qty)))
                    res += [(quant, abs(quant.qty))]
                    remaining_quantity -= abs(quant.qty)
                elif float_compare(remaining_quantity, 0.0, precision_rounding=rounding) != 0:
                    # reserved_quants.append(self._ReservedQuant(quant, remaining_quantity))
                    res += [(quant, remaining_quantity)]
                    remaining_quantity = 0
            offset += 10
            quants = self.search(domain, order=order, limit=10, offset=offset)

        if float_compare(remaining_quantity, 0, precision_rounding=rounding) > 0:
            res.append((None, remaining_quantity))

        return res

    # Misc tools
    # ----------------------------------------------------------------------

    def _get_top_level_packages(self, product_to_location):
        """ This method searches for as much possible higher level packages that
        can be moved as a single operation, given a list of quants to move and
        their suggested destination, and returns the list of matching packages. """
        top_lvl_packages = self.env['stock.quant.package']
        for package in self.mapped('package_id'):
            all_in = True
            top_package = self.env['stock.quant.package']
            while package:
                if any(quant not in self for quant in package.get_content()):
                    all_in = False
                if all_in:
                    destinations = set([product_to_location[product] for product in package.get_content().mapped('product_id')])
                    if len(destinations) > 1:
                        all_in = False
                if all_in:
                    top_package = package
                    package = package.parent_id
                else:
                    package = False
            top_lvl_packages |= top_package
        return top_lvl_packages

    @api.multi
    def _get_latest_move(self):
        latest_move = self.history_ids[0]
        for move in self.history_ids:
            if move.date > latest_move.date:
                latest_move = move
        return latest_move

    @api.multi
    def _quant_split(self, qty):
        self.ensure_one()
        rounding = self.product_id.uom_id.rounding
        if float_compare(abs(self.qty), abs(qty), precision_rounding=rounding) <= 0: # if quant <= qty in abs, take it entirely
            return False
        qty_round = float_round(qty, precision_rounding=rounding)
        new_qty_round = float_round(self.qty - qty, precision_rounding=rounding)
        # Fetch the history_ids manually as it will not do a join with the stock moves then (=> a lot faster)
        self._cr.execute("""SELECT move_id FROM stock_quant_move_rel WHERE quant_id = %s""", (self.id,))
        res = self._cr.fetchall()
        new_quant = self.sudo().copy(default={'qty': new_qty_round, 'history_ids': [(4, x[0]) for x in res]})
        self.sudo().write({'qty': qty_round})
        return new_quant


class QuantPackage(models.Model):
    """ Packages containing quants and/or other packages """
    _name = "stock.quant.package"
    _description = "Physical Packages"
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'name'
    _order = 'parent_left'

    name = fields.Char(
        'Package Reference', copy=False, index=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('stock.quant.package') or _('Unknown Pack'))
    quant_ids = fields.One2many('stock.quant', 'package_id', 'Bulk Content', readonly=True)
    parent_id = fields.Many2one(
        'stock.quant.package', 'Parent Package',
        ondelete='restrict', readonly=True,
        help="The package containing this item")
    ancestor_ids = fields.One2many('stock.quant.package', string='Ancestors', compute='_compute_ancestor_ids')
    children_quant_ids = fields.One2many('stock.quant', string='All Bulk Content', compute='_compute_children_quant_ids')
    children_ids = fields.One2many('stock.quant.package', 'parent_id', 'Contained Packages', readonly=True)
    parent_left = fields.Integer('Left Parent', index=True)
    parent_right = fields.Integer('Right Parent', index=True)
    packaging_id = fields.Many2one(
        'product.packaging', 'Package Type', index=True,
        help="This field should be completed only if everything inside the package share the same product, otherwise it doesn't really makes sense.")
    location_id = fields.Many2one(
        'stock.location', 'Location', compute='_compute_package_info', search='_search_location',
        index=True, readonly=True)
    company_id = fields.Many2one(
        'res.company', 'Company', compute='_compute_package_info', search='_search_company',
        index=True, readonly=True)
    owner_id = fields.Many2one(
        'res.partner', 'Owner', compute='_compute_package_info', search='_search_owner',
        index=True, readonly=True)

    @api.one
    @api.depends('parent_id', 'children_ids')
    def _compute_ancestor_ids(self):
        self.ancestor_ids = self.env['stock.quant.package'].search([('id', 'parent_of', self.id)]).ids

    @api.multi
    @api.depends('parent_id', 'children_ids', 'quant_ids.package_id')
    def _compute_children_quant_ids(self):
        for package in self:
            if package.id:
                package.children_quant_ids = self.env['stock.quant'].search([('package_id', 'child_of', package.id)]).ids

    @api.depends('quant_ids.package_id', 'quant_ids.location_id', 'quant_ids.company_id', 'quant_ids.owner_id', 'ancestor_ids')
    def _compute_package_info(self):
        for package in self:
            quants = package.children_quant_ids
            if quants:
                values = quants[0]
            else:
                values = {'location_id': False, 'company_id': self.env.user.company_id.id, 'owner_id': False}
            package.location_id = values['location_id']
            package.company_id = values['company_id']
            package.owner_id = values['owner_id']

    @api.multi
    def name_get(self):
        return self._compute_complete_name().items()

    def _compute_complete_name(self):
        """ Forms complete name of location from parent location to child location. """
        res = {}
        for package in self:
            current = package
            name = current.name
            while current.parent_id:
                name = '%s / %s' % (current.parent_id.name, name)
                current = current.parent_id
            res[package.id] = name
        return res

    def _search_location(self, operator, value):
        if value:
            packs = self.search([('quant_ids.location_id', operator, value)])
        else:
            packs = self.search([('quant_ids', operator, value)])
        if packs:
            return [('id', 'parent_of', packs.ids)]
        else:
            return [('id', '=', False)]

    def _search_company(self, operator, value):
        if value:
            packs = self.search([('quant_ids.company_id', operator, value)])
        else:
            packs = self.search([('quant_ids', operator, value)])
        if packs:
            return [('id', 'parent_of', packs.ids)]
        else:
            return [('id', '=', False)]

    def _search_owner(self, operator, value):
        if value:
            packs = self.search([('quant_ids.owner_id', operator, value)])
        else:
            packs = self.search([('quant_ids', operator, value)])
        if packs:
            return [('id', 'parent_of', packs.ids)]
        else:
            return [('id', '=', False)]

    def _check_location_constraint(self):
        '''checks that all quants in a package are stored in the same location. This function cannot be used
           as a constraint because it needs to be checked on pack operations (they may not call write on the
           package)
        '''
        for pack in self:
            parent = pack
            while parent.parent_id:
                parent = parent.parent_id
            locations = parent.get_content().filtered(lambda quant: quant.qty > 0.0).mapped('location_id')
            if len(locations) != 1:
                raise UserError(_('Everything inside a package should be in the same location'))
        return True

    @api.multi
    def action_view_related_picking(self):
        """ Returns an action that display the picking related to this
        package (source or destination).
        """
        self.ensure_one()
        pickings = self.env['stock.picking'].search(['|', ('pack_operation_ids.package_id', '=', self.id), ('pack_operation_ids.result_package_id', '=', self.id)])
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        action['domain'] = [('id', 'in', pickings.ids)]
        return action

    @api.multi
    def unpack(self):
        for package in self:
            # TDE FIXME: why superuser ?
            package.mapped('quant_ids').sudo().write({'package_id': package.parent_id.id})
            package.mapped('children_ids').write({'parent_id': package.parent_id.id})
        return self.env['ir.actions.act_window'].for_xml_id('stock', 'action_package_view')

    @api.multi
    def view_content_package(self):
        action = self.env['ir.actions.act_window'].for_xml_id('stock', 'quantsact')
        action['domain'] = [('id', 'in', self._get_contained_quants().ids)]
        return action
    get_content_package = view_content_package

    def _get_contained_quants(self):
        return self.env['stock.quant'].search([('package_id', 'child_of', self.ids)])
    get_content = _get_contained_quants

    def _get_all_products_quantities(self):
        '''This function computes the different product quantities for the given package
        '''
        # TDE CLEANME: probably to move somewhere else, like in pack op
        res = {}
        for quant in self._get_contained_quants():
            if quant.product_id not in res:
                res[quant.product_id] = 0
            res[quant.product_id] += quant.qty
        return res
