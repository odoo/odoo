# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import OperationalError, Error

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero, float_round

import logging

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _name = 'stock.quant'
    _description = 'Quants'
    _rec_name = 'product_id'

    def _domain_location_id(self):
        if not self._is_inventory_mode():
            return
        return [('usage', 'in', ['internal', 'transit'])]

    def _domain_lot_id(self):
        if not self._is_inventory_mode():
            return
        domain = [
            "'|'",
                "('company_id', '=', company_id)",
                "('company_id', '=', False)"
        ]
        if self.env.context.get('active_model') == 'product.product':
            domain.insert(0, "('product_id', '=', %s)" % self.env.context.get('active_id'))
        if self.env.context.get('active_model') == 'product.template':
            product_template = self.env['product.template'].browse(self.env.context.get('active_id'))
            if product_template.exists():
                domain.insert(0, "('product_id', 'in', %s)" % product_template.product_variant_ids.ids)
        return '[' + ', '.join(domain) + ']'

    def _domain_product_id(self):
        if not self._is_inventory_mode():
            return
        domain = [('type', '=', 'product')]
        if self.env.context.get('product_tmpl_id'):
            domain = expression.AND([domain, [('product_tmpl_id', '=', self.env.context['product_tmpl_id'])]])
        return domain

    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=lambda self: self._domain_product_id(),
        ondelete='restrict', readonly=True, required=True, index=True, check_company=True)
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product Template',
        related='product_id.product_tmpl_id', readonly=False)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        readonly=True, related='product_id.uom_id')
    company_id = fields.Many2one(related='location_id.company_id', string='Company', store=True, readonly=True)
    location_id = fields.Many2one(
        'stock.location', 'Location',
        domain=lambda self: self._domain_location_id(),
        auto_join=True, ondelete='restrict', readonly=True, required=True, index=True, check_company=True)
    lot_id = fields.Many2one(
        'stock.production.lot', 'Lot/Serial Number',
        ondelete='restrict', readonly=True, check_company=True,
        domain=lambda self: self._domain_lot_id())
    package_id = fields.Many2one(
        'stock.quant.package', 'Package',
        domain="[('location_id', '=', location_id)]",
        help='The package containing this quant', readonly=True, ondelete='restrict', check_company=True)
    owner_id = fields.Many2one(
        'res.partner', 'Owner',
        help='This is the owner of the quant', readonly=True, check_company=True)
    quantity = fields.Float(
        'Quantity',
        help='Quantity of products in this quant, in the default unit of measure of the product',
        readonly=True)
    inventory_quantity = fields.Float(
        'Inventoried Quantity', compute='_compute_inventory_quantity',
        inverse='_set_inventory_quantity', groups='stock.group_stock_manager')
    reserved_quantity = fields.Float(
        'Reserved Quantity',
        default=0.0,
        help='Quantity of reserved products in this quant, in the default unit of measure of the product',
        readonly=True, required=True)
    in_date = fields.Datetime('Incoming Date', readonly=True)
    tracking = fields.Selection(related='product_id.tracking', readonly=True)
    on_hand = fields.Boolean('On Hand', store=False, search='_search_on_hand')

    @api.depends('quantity')
    def _compute_inventory_quantity(self):
        if not self._is_inventory_mode():
            self.inventory_quantity = 0
            return
        for quant in self:
            quant.inventory_quantity = quant.quantity

    def _set_inventory_quantity(self):
        """ Inverse method to create stock move when `inventory_quantity` is set
        (`inventory_quantity` is only accessible in inventory mode).
        """
        if not self._is_inventory_mode():
            return
        for quant in self:
            # Get the quantity to create a move for.
            rounding = quant.product_id.uom_id.rounding
            diff = float_round(quant.inventory_quantity - quant.quantity, precision_rounding=rounding)
            diff_float_compared = float_compare(diff, 0, precision_rounding=rounding)
            # Create and vaidate a move so that the quant matches its `inventory_quantity`.
            if diff_float_compared == 0:
                continue
            elif diff_float_compared > 0:
                move_vals = quant._get_inventory_move_values(diff, quant.product_id.with_context(force_company=quant.company_id.id or self.env.company.id).property_stock_inventory, quant.location_id)
            else:
                move_vals = quant._get_inventory_move_values(-diff, quant.location_id, quant.product_id.with_context(force_company=quant.company_id.id or self.env.company.id).property_stock_inventory, out=True)
            move = quant.env['stock.move'].with_context(inventory_mode=False).create(move_vals)
            move._action_done()

    def _search_on_hand(self, operator, value):
        """Handle the "on_hand" filter, indirectly calling `_get_domain_locations`."""
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise UserError(_('Operation not supported'))
        domain_loc = self.env['product.product']._get_domain_locations()[0]
        quant_ids = [l['id'] for l in self.env['stock.quant'].search_read(domain_loc, ['id'])]
        if (operator == '!=' and value is True) or (operator == '=' and value is False):
            domain_operator = 'not in'
        else:
            domain_operator = 'in'
        return [('id', domain_operator, quant_ids)]

    @api.model
    def create(self, vals):
        """ Override to handle the "inventory mode" and create a quant as
        superuser the conditions are met.
        """
        if self._is_inventory_mode() and 'inventory_quantity' in vals:
            allowed_fields = self._get_inventory_fields_create()
            if any([field for field in vals.keys() if field not in allowed_fields]):
                raise UserError(_("Quant's creation is restricted, you can't do this operation."))
            inventory_quantity = vals.pop('inventory_quantity')

            # Create an empty quant or write on a similar one.
            product = self.env['product.product'].browse(vals['product_id'])
            location = self.env['stock.location'].browse(vals['location_id'])
            lot_id = self.env['stock.production.lot'].browse(vals.get('lot_id'))
            package_id = self.env['stock.quant.package'].browse(vals.get('package_id'))
            owner_id = self.env['res.partner'].browse(vals.get('owner_id'))
            quant = self._gather(product, location, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True)
            if quant:
                quant = quant[0]
            else:
                quant = self.sudo().create(vals)
            # Set the `inventory_quantity` field to create the necessary move.
            quant.inventory_quantity = inventory_quantity
            return quant
        res = super(StockQuant, self).create(vals)
        if self._is_inventory_mode():
            res._check_company()
        return res

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """ Override to handle the "inventory mode" and set the `inventory_quantity`
        in view list grouped.
        """
        result = super(StockQuant, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        if self._is_inventory_mode():
            for record in result:
                record['inventory_quantity'] = record.get('quantity', 0)
        return result

    def write(self, vals):
        """ Override to handle the "inventory mode" and create the inventory move. """
        if self._is_inventory_mode() and 'inventory_quantity' in vals:
            if any(quant.location_id.usage == 'inventory' for quant in self):
                # Do nothing when user tries to modify manually a inventory loss
                return
            allowed_fields = self._get_inventory_fields_write()
            if any([field for field in vals.keys() if field not in allowed_fields]):
                raise UserError(_("Quant's edition is restricted, you can't do this operation."))
            self = self.sudo()
            return super(StockQuant, self).write(vals)
        return super(StockQuant, self).write(vals)

    def action_view_stock_moves(self):
        self.ensure_one()
        action = self.env.ref('stock.stock_move_line_action').read()[0]
        action['domain'] = [
            ('product_id', '=', self.product_id.id),
            '|',
                ('location_id', '=', self.location_id.id),
                ('location_dest_id', '=', self.location_id.id),
            ('lot_id', '=', self.lot_id.id),
            '|',
                ('package_id', '=', self.package_id.id),
                ('result_package_id', '=', self.package_id.id),
        ]
        return action

    @api.model
    def action_view_quants(self):
        self = self.with_context(search_default_internal_loc=1)
        if self.user_has_groups('stock.group_production_lot,stock.group_stock_multi_locations'):
            # fixme: erase the following condition when it'll be possible to create a new record
            # from a empty grouped editable list without go through the form view.
            if self.search_count([
                ('company_id', '=', self.env.company.id),
                ('location_id.usage', 'in', ['internal', 'transit'])
            ]):
                self = self.with_context(
                    search_default_productgroup=1,
                    search_default_locationgroup=1
                )
        if not self.user_has_groups('stock.group_stock_multi_locations'):
            company_user = self.env.company
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
            if warehouse:
                self = self.with_context(default_location_id=warehouse.lot_stock_id.id)

        # If user have rights to write on quant, we set quants in inventory mode.
        if self.user_has_groups('stock.group_stock_manager'):
            self = self.with_context(inventory_mode=True)
        return self._get_quants_action(extend=True)

    @api.constrains('product_id')
    def check_product_id(self):
        if any(elem.product_id.type != 'product' for elem in self):
            raise ValidationError(_('Quants cannot be created for consumables or services.'))

    @api.constrains('quantity')
    def check_quantity(self):
        for quant in self:
            if float_compare(quant.quantity, 1, precision_rounding=quant.product_uom_id.rounding) > 0 and quant.lot_id and quant.product_id.tracking == 'serial':
                message_base = _('A serial number should only be linked to a single product.')
                message_quant = _('Please check the following serial number (name, id): ')
                message_sn = '(%s, %s)' % (quant.lot_id.name, quant.lot_id.id)
                raise ValidationError("\n".join([message_base, message_quant, message_sn]))

    @api.constrains('location_id')
    def check_location_id(self):
        for quant in self:
            if quant.location_id.usage == 'view':
                raise ValidationError(_('You cannot take products from or deliver products to a location of type "view".'))

    def _compute_name(self):
        for quant in self:
            quant.name = '%s: %s%s' % (quant.lot_id.name or quant.product_id.code or '', quant.quantity, quant.product_id.uom_id.name)

    @api.model
    def _get_removal_strategy(self, product_id, location_id):
        if product_id.categ_id.removal_strategy_id:
            return product_id.categ_id.removal_strategy_id.method
        loc = location_id
        while loc:
            if loc.removal_strategy_id:
                return loc.removal_strategy_id.method
            loc = loc.location_id
        return 'fifo'

    @api.model
    def _get_removal_strategy_order(self, removal_strategy):
        if removal_strategy == 'fifo':
            return 'in_date ASC NULLS FIRST, id'
        elif removal_strategy == 'lifo':
            return 'in_date DESC NULLS LAST, id desc'
        raise UserError(_('Removal strategy %s not implemented.') % (removal_strategy,))

    def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        self.env['stock.quant'].flush(['location_id', 'owner_id', 'package_id', 'lot_id', 'product_id'])
        self.env['product.product'].flush(['virtual_available'])
        removal_strategy = self._get_removal_strategy(product_id, location_id)
        removal_strategy_order = self._get_removal_strategy_order(removal_strategy)
        domain = [
            ('product_id', '=', product_id.id),
        ]
        if not strict:
            if lot_id:
                domain = expression.AND([[('lot_id', '=', lot_id.id)], domain])
            if package_id:
                domain = expression.AND([[('package_id', '=', package_id.id)], domain])
            if owner_id:
                domain = expression.AND([[('owner_id', '=', owner_id.id)], domain])
            domain = expression.AND([[('location_id', 'child_of', location_id.id)], domain])
        else:
            domain = expression.AND([[('lot_id', '=', lot_id and lot_id.id or False)], domain])
            domain = expression.AND([[('package_id', '=', package_id and package_id.id or False)], domain])
            domain = expression.AND([[('owner_id', '=', owner_id and owner_id.id or False)], domain])
            domain = expression.AND([[('location_id', '=', location_id.id)], domain])

        # Copy code of _search for special NULLS FIRST/LAST order
        self.check_access_rights('read')
        query = self._where_calc(domain)
        self._apply_ir_rules(query, 'read')
        from_clause, where_clause, where_clause_params = query.get_sql()
        where_str = where_clause and (" WHERE %s" % where_clause) or ''
        query_str = 'SELECT "%s".id FROM ' % self._table + from_clause + where_str + " ORDER BY "+ removal_strategy_order
        self._cr.execute(query_str, where_clause_params)
        res = self._cr.fetchall()
        # No uniquify list necessary as auto_join is not applied anyways...
        return self.browse([x[0] for x in res])

    @api.model
    def _get_available_quantity(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, allow_negative=False):
        """ Return the available quantity, i.e. the sum of `quantity` minus the sum of
        `reserved_quantity`, for the set of quants sharing the combination of `product_id,
        location_id` if `strict` is set to False or sharing the *exact same characteristics*
        otherwise.
        This method is called in the following usecases:
            - when a stock move checks its availability
            - when a stock move actually assign
            - when editing a move line, to check if the new value is forced or not
            - when validating a move line with some forced values and have to potentially unlink an
              equivalent move line in another picking
        In the two first usecases, `strict` should be set to `False`, as we don't know what exact
        quants we'll reserve, and the characteristics are meaningless in this context.
        In the last ones, `strict` should be set to `True`, as we work on a specific set of
        characteristics.

        :return: available quantity as a float
        """
        self = self.sudo()
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
        rounding = product_id.uom_id.rounding
        if product_id.tracking == 'none':
            available_quantity = sum(quants.mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
            if allow_negative:
                return available_quantity
            else:
                return available_quantity if float_compare(available_quantity, 0.0, precision_rounding=rounding) >= 0.0 else 0.0
        else:
            availaible_quantities = {lot_id: 0.0 for lot_id in list(set(quants.mapped('lot_id'))) + ['untracked']}
            for quant in quants:
                if not quant.lot_id:
                    availaible_quantities['untracked'] += quant.quantity - quant.reserved_quantity
                else:
                    availaible_quantities[quant.lot_id] += quant.quantity - quant.reserved_quantity
            if allow_negative:
                return sum(availaible_quantities.values())
            else:
                return sum([available_quantity for available_quantity in availaible_quantities.values() if float_compare(available_quantity, 0, precision_rounding=rounding) > 0])

    @api.onchange('location_id', 'product_id', 'lot_id', 'package_id', 'owner_id')
    def _onchange_location_or_product_id(self):
        vals = {}

        # Once the new line is complete, fetch the new theoretical values.
        if self.product_id and self.location_id:
            # Sanity check if a lot has been set.
            if self.lot_id:
                if self.tracking == 'none' or self.product_id != self.lot_id.product_id:
                    vals['lot_id'] = None

            quants = self._gather(self.product_id, self.location_id, lot_id=self.lot_id, package_id=self.package_id, owner_id=self.owner_id, strict=True)
            reserved_quantity = sum(quants.mapped('reserved_quantity'))
            quantity = sum(quants.mapped('quantity'))

            vals['reserved_quantity'] = reserved_quantity
            # Update `quantity` only if the user manually updated `inventory_quantity`.
            if float_compare(self.quantity, self.inventory_quantity, precision_rounding=self.product_uom_id.rounding) == 0:
                vals['quantity'] = quantity
            # Special case: directly set the quantity to one for serial numbers,
            # it'll trigger `inventory_quantity` compute.
            if self.lot_id and self.tracking == 'serial':
                vals['quantity'] = 1

        if vals:
            self.update(vals)

    @api.onchange('inventory_quantity')
    def _onchange_inventory_quantity(self):
        if self.location_id and self.location_id.usage == 'inventory':
            warning = {
                'title': _('You cannot modify inventory loss quantity'),
                'message': _(
                    'Editing quantities in an Inventory Adjustment location is forbidden,'
                    'those locations are used as counterpart when correcting the quantities.'
                )
            }
            return {'warning': warning}

    @api.model
    def _update_available_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, in_date=None):
        """ Increase or decrease `reserved_quantity` of a set of quants for a given set of
        product_id/location_id/lot_id/package_id/owner_id.

        :param product_id:
        :param location_id:
        :param quantity:
        :param lot_id:
        :param package_id:
        :param owner_id:
        :param datetime in_date: Should only be passed when calls to this method are done in
                                 order to move a quant. When creating a tracked quant, the
                                 current datetime will be used.
        :return: tuple (available_quantity, in_date as a datetime)
        """
        self = self.sudo()
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True)

        incoming_dates = [d for d in quants.mapped('in_date') if d]
        incoming_dates = [fields.Datetime.from_string(incoming_date) for incoming_date in incoming_dates]
        if in_date:
            incoming_dates += [in_date]
        # If multiple incoming dates are available for a given lot_id/package_id/owner_id, we
        # consider only the oldest one as being relevant.
        if incoming_dates:
            in_date = fields.Datetime.to_string(min(incoming_dates))
        else:
            in_date = fields.Datetime.now()

        for quant in quants:
            try:
                with self._cr.savepoint():
                    self._cr.execute("SELECT 1 FROM stock_quant WHERE id = %s FOR UPDATE NOWAIT", [quant.id], log_exceptions=False)
                    quant.write({
                        'quantity': quant.quantity + quantity,
                        'in_date': in_date,
                    })
                    break
            except OperationalError as e:
                if e.pgcode == '55P03':  # could not obtain the lock
                    continue
                else:
                    raise
        else:
            self.create({
                'product_id': product_id.id,
                'location_id': location_id.id,
                'quantity': quantity,
                'lot_id': lot_id and lot_id.id,
                'package_id': package_id and package_id.id,
                'owner_id': owner_id and owner_id.id,
                'in_date': in_date,
            })
        return self._get_available_quantity(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=False, allow_negative=True), fields.Datetime.from_string(in_date)

    @api.model
    def _update_reserved_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, strict=False):
        """ Increase the reserved quantity, i.e. increase `reserved_quantity` for the set of quants
        sharing the combination of `product_id, location_id` if `strict` is set to False or sharing
        the *exact same characteristics* otherwise. Typically, this method is called when reserving
        a move or updating a reserved move line. When reserving a chained move, the strict flag
        should be enabled (to reserve exactly what was brought). When the move is MTS,it could take
        anything from the stock, so we disable the flag. When editing a move line, we naturally
        enable the flag, to reflect the reservation according to the edition.

        :return: a list of tuples (quant, quantity_reserved) showing on which quant the reservation
            was done and how much the system was able to reserve on it
        """
        self = self.sudo()
        rounding = product_id.uom_id.rounding
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
        reserved_quants = []

        if float_compare(quantity, 0, precision_rounding=rounding) > 0:
            # if we want to reserve
            available_quantity = self._get_available_quantity(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
            if float_compare(quantity, available_quantity, precision_rounding=rounding) > 0:
                raise UserError(_('It is not possible to reserve more products of %s than you have in stock.') % product_id.display_name)
        elif float_compare(quantity, 0, precision_rounding=rounding) < 0:
            # if we want to unreserve
            available_quantity = sum(quants.mapped('reserved_quantity'))
            if float_compare(abs(quantity), available_quantity, precision_rounding=rounding) > 0:
                raise UserError(_('It is not possible to unreserve more products of %s than you have in stock.') % product_id.display_name)
        else:
            return reserved_quants

        for quant in quants:
            if float_compare(quantity, 0, precision_rounding=rounding) > 0:
                max_quantity_on_quant = quant.quantity - quant.reserved_quantity
                if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
                    continue
                max_quantity_on_quant = min(max_quantity_on_quant, quantity)
                quant.reserved_quantity += max_quantity_on_quant
                reserved_quants.append((quant, max_quantity_on_quant))
                quantity -= max_quantity_on_quant
                available_quantity -= max_quantity_on_quant
            else:
                max_quantity_on_quant = min(quant.reserved_quantity, abs(quantity))
                quant.reserved_quantity -= max_quantity_on_quant
                reserved_quants.append((quant, -max_quantity_on_quant))
                quantity += max_quantity_on_quant
                available_quantity += max_quantity_on_quant

            if float_is_zero(quantity, precision_rounding=rounding) or float_is_zero(available_quantity, precision_rounding=rounding):
                break
        return reserved_quants

    @api.model
    def _unlink_zero_quants(self):
        """ _update_available_quantity may leave quants with no
        quantity and no reserved_quantity. It used to directly unlink
        these zero quants but this proved to hurt the performance as
        this method is often called in batch and each unlink invalidate
        the cache. We defer the calls to unlink in this method.
        """
        precision_digits = max(6, self.sudo().env.ref('product.decimal_product_uom').digits * 2)
        # Use a select instead of ORM search for UoM robustness.
        query = """SELECT id FROM stock_quant WHERE (round(quantity::numeric, %s) = 0 OR quantity IS NULL) AND round(reserved_quantity::numeric, %s) = 0;"""
        params = (precision_digits, precision_digits)
        self.env.cr.execute(query, params)
        quant_ids = self.env['stock.quant'].browse([quant['id'] for quant in self.env.cr.dictfetchall()])
        quant_ids.sudo().unlink()

    @api.model
    def _merge_quants(self):
        """ In a situation where one transaction is updating a quant via
        `_update_available_quantity` and another concurrent one calls this function with the same
        argument, we’ll create a new quant in order for these transactions to not rollback. This
        method will find and deduplicate these quants.
        """
        query = """WITH
                        dupes AS (
                            SELECT min(id) as to_update_quant_id,
                                (array_agg(id ORDER BY id))[2:array_length(array_agg(id), 1)] as to_delete_quant_ids,
                                SUM(reserved_quantity) as reserved_quantity,
                                SUM(quantity) as quantity
                            FROM stock_quant
                            GROUP BY product_id, company_id, location_id, lot_id, package_id, owner_id, in_date
                            HAVING count(id) > 1
                        ),
                        _up AS (
                            UPDATE stock_quant q
                                SET quantity = d.quantity,
                                    reserved_quantity = d.reserved_quantity
                            FROM dupes d
                            WHERE d.to_update_quant_id = q.id
                        )
                   DELETE FROM stock_quant WHERE id in (SELECT unnest(to_delete_quant_ids) from dupes)
        """
        try:
            with self.env.cr.savepoint():
                self.env.cr.execute(query)
        except Error as e:
            _logger.info('an error occured while merging quants: %s', e.pgerror)

    @api.model
    def _quant_tasks(self):
        self._merge_quants()
        self._unlink_zero_quants()

    @api.model
    def _is_inventory_mode(self):
        """ Used to control whether a quant was written on or created during an
        "inventory session", meaning a mode where we need to create the stock.move
        record necessary to be consistent with the `inventory_quantity` field.
        """
        return self.env.context.get('inventory_mode') is True and self.user_has_groups('stock.group_stock_manager')

    @api.model
    def _get_inventory_fields_create(self):
        """ Returns a list of fields user can edit when he want to create a quant in `inventory_mode`.
        """
        return ['product_id', 'location_id', 'lot_id', 'package_id', 'owner_id', 'inventory_quantity']

    @api.model
    def _get_inventory_fields_write(self):
        """ Returns a list of fields user can edit when he want to edit a quant in `inventory_mode`.
        """
        return ['inventory_quantity']

    def _get_inventory_move_values(self, qty, location_id, location_dest_id, out=False):
        """ Called when user manually set a new quantity (via `inventory_quantity`)
        just before creating the corresponding stock move.

        :param location_id: `stock.location`
        :param location_dest_id: `stock.location`
        :param out: boolean to set on True when the move go to inventory adjustment location.
        :return: dict with all values needed to create a new `stock.move` with its move line.
        """
        self.ensure_one()
        return {
            'name': _('Product Quantity Updated'),
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'product_uom_qty': qty,
            'company_id': self.company_id.id or self.env.company.id,
            'state': 'confirmed',
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
            'move_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'product_uom_id': self.product_uom_id.id,
                'qty_done': qty,
                'location_id': location_id.id,
                'location_dest_id': location_dest_id.id,
                'company_id': self.company_id.id or self.env.company.id,
                'lot_id': self.lot_id.id,
                'package_id': out and self.package_id.id or False,
                'result_package_id': (not out) and self.package_id.id or False,
                'owner_id': self.owner_id.id,
            })]
        }

    @api.model
    def _get_quants_action(self, domain=None, extend=False):
        """ Returns an action to open quant view.
        Depending of the context (user have right to be inventory mode or not),
        the list view will be editable or readonly.

        :param domain: List for the domain, empty by default.
        :param extend: If True, enables form, graph and pivot views. False by default.
        """
        self._quant_tasks()
        ctx = dict(self.env.context or {})
        ctx.pop('group_by', None)
        action = {
            'name': _('Update Quantity'),
            'view_type': 'tree',
            'view_mode': 'list',
            'res_model': 'stock.quant',
            'type': 'ir.actions.act_window',
            'context': ctx,
            'domain': domain or [],
            'help': """
                <p class="o_view_nocontent_empty_folder">No Stock On Hand</p>
                <p>This analysis gives you an overview of the current stock
                level of your products.</p>
                """
        }

        if self._is_inventory_mode():
            action['view_id'] = self.env.ref('stock.view_stock_quant_tree_editable').id
            # fixme: erase the following condition when it'll be possible to create a new record
            # from a empty grouped editable list without go through the form view.
            if not self.search_count([
                ('company_id', '=', self.env.company.id),
                ('location_id.usage', 'in', ['internal', 'transit'])
            ]):
                action['context'].update({
                    'search_default_productgroup': 0,
                    'search_default_locationgroup': 0
                })
        else:
            action['view_id'] = self.env.ref('stock.view_stock_quant_tree').id
            # Enables form view in readonly list
            action.update({
                'view_mode': 'tree,form',
                'views': [
                    (action['view_id'], 'list'),
                    (self.env.ref('stock.view_stock_quant_form').id, 'form'),
                ],
            })
        if extend:
            action.update({
                'view_mode': 'tree,form,pivot,graph',
                'views': [
                    (action['view_id'], 'list'),
                    (self.env.ref('stock.view_stock_quant_form').id, 'form'),
                    (self.env.ref('stock.view_stock_quant_pivot').id, 'pivot'),
                    (self.env.ref('stock.stock_quant_view_graph').id, 'graph'),
                ],
            })
        return action


class QuantPackage(models.Model):
    """ Packages containing quants and/or other packages """
    _name = "stock.quant.package"
    _description = "Packages"
    _order = 'name'

    name = fields.Char(
        'Package Reference', copy=False, index=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('stock.quant.package') or _('Unknown Pack'))
    quant_ids = fields.One2many('stock.quant', 'package_id', 'Bulk Content', readonly=True,
        domain=['|', ('quantity', '!=', 0), ('reserved_quantity', '!=', 0)])
    packaging_id = fields.Many2one(
        'product.packaging', 'Package Type', index=True, check_company=True)
    location_id = fields.Many2one(
        'stock.location', 'Location', compute='_compute_package_info',
        index=True, readonly=True, store=True)
    company_id = fields.Many2one(
        'res.company', 'Company', compute='_compute_package_info',
        index=True, readonly=True, store=True)
    owner_id = fields.Many2one(
        'res.partner', 'Owner', compute='_compute_package_info', search='_search_owner',
        index=True, readonly=True, compute_sudo=True)

    @api.depends('quant_ids.package_id', 'quant_ids.location_id', 'quant_ids.company_id', 'quant_ids.owner_id', 'quant_ids.quantity', 'quant_ids.reserved_quantity')
    def _compute_package_info(self):
        for package in self:
            values = {'location_id': False, 'owner_id': False}
            if package.quant_ids:
                values['location_id'] = package.quant_ids[0].location_id
                if all(q.owner_id == package.quant_ids[0].owner_id for q in package.quant_ids):
                    values['owner_id'] = package.quant_ids[0].owner_id
                if all(q.company_id == package.quant_ids[0].company_id for q in package.quant_ids):
                    values['company_id'] = package.quant_ids[0].company_id
            package.location_id = values['location_id']
            package.company_id = values.get('company_id')
            package.owner_id = values['owner_id']

    def name_get(self):
        return list(self._compute_complete_name().items())

    def _compute_complete_name(self):
        """ Forms complete name of location from parent location to child location. """
        res = {}
        for package in self:
            name = package.name
            res[package.id] = name
        return res

    def _search_owner(self, operator, value):
        if value:
            packs = self.search([('quant_ids.owner_id', operator, value)])
        else:
            packs = self.search([('quant_ids', operator, value)])
        if packs:
            return [('id', 'parent_of', packs.ids)]
        else:
            return [('id', '=', False)]

    def unpack(self):
        for package in self:
            move_line_to_modify = self.env['stock.move.line'].search([
                ('package_id', '=', package.id),
                ('state', 'in', ('assigned', 'partially_available')),
                ('product_qty', '!=', 0),
            ])
            move_line_to_modify.write({'package_id': False})
            package.mapped('quant_ids').sudo().write({'package_id': False})

        # Quant clean-up, mostly to avoid multiple quants of the same product. For example, unpack
        # 2 packages of 50, then reserve 100 => a quant of -50 is created at transfer validation.
        self.env['stock.quant']._merge_quants()
        self.env['stock.quant']._unlink_zero_quants()

    def action_view_picking(self):
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        domain = ['|', ('result_package_id', 'in', self.ids), ('package_id', 'in', self.ids)]
        pickings = self.env['stock.move.line'].search(domain).mapped('picking_id')
        action['domain'] = [('id', 'in', pickings.ids)]
        return action

    def view_content_package(self):
        action = self.env['ir.actions.act_window'].for_xml_id('stock', 'quantsact')
        action['domain'] = [('id', 'in', self._get_contained_quants().ids)]
        return action

    def _get_contained_quants(self):
        return self.env['stock.quant'].search([('package_id', 'in', self.ids)])

    def _get_all_products_quantities(self):
        '''This function computes the different product quantities for the given package
        '''
        # TDE CLEANME: probably to move somewhere else, like in pack op
        res = {}
        for quant in self._get_contained_quants():
            if quant.product_id not in res:
                res[quant.product_id] = 0
            res[quant.product_id] += quant.quantity
        return res

