# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import OperationalError

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


class StockQuant(models.Model):
    _name = 'stock.quant'
    _description = 'Quants'

    product_id = fields.Many2one(
        'product.product', 'Product',
        ondelete='restrict', readonly=True, required=True)
    product_uom_id = fields.Many2one(
        'product.uom', 'Unit of Measure',
        readonly=True, related='product_id.uom_id')
    company_id = fields.Many2one(related='location_id.company_id',
        string='Company', store=True, readonly=True)
    location_id = fields.Many2one(
        'stock.location', 'Location',
        auto_join=True, ondelete='restrict', readonly=True, required=True)
    lot_id = fields.Many2one(
        'stock.production.lot', 'Lot/Serial Number',
        ondelete='restrict', readonly=True)
    package_id = fields.Many2one(
        'stock.quant.package', 'Package',
        help='The package containing this quant', readonly=True, ondelete='restrict')
    owner_id = fields.Many2one(
        'res.partner', 'Owner',
        help='This is the owner of the quant', readonly=True)
    quantity = fields.Float(
        'Quantity',
        help='Quantity of products in this quant, in the default unit of measure of the product',
        readonly=True, required=True, oldname='qty')
    reserved_quantity = fields.Float(
        'Reserved Quantity',
        default=0.0,
        help='Quantity of reserved products in this quant, in the default unit of measure of the product',
        readonly=True, required=True)
    in_date = fields.Datetime('Incoming Date', readonly=True)

    @api.multi
    @api.constrains('product_id')
    def check_product_id(self):
        if any(elem.product_id.type != 'product' for elem in self):
            raise ValidationError(_('Quants cannot be created for consumables or services.'))

    @api.multi
    @api.constrains('quantity')
    def check_quantity(self):
        for quant in self:
            if quant.quantity > 1 and quant.lot_id and quant.product_id.tracking == 'serial':
                raise ValidationError(_('A serial number should only be linked to a single product.'))

    @api.multi
    @api.constrains('in_date', 'lot_id')
    def check_in_date(self):
        for quant in self:
            if quant.in_date and not quant.lot_id:
                raise ValidationError(_('An incoming date cannot be set to an untracked product.'))

    @api.one
    def _compute_name(self):
        self.name = '%s: %s%s' % (self.lot_id.name or self.product_id.code or '', self.quantity, self.product_id.uom_id.name)

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
            return 'in_date, id'
        elif removal_strategy == 'lifo':
            return 'in_date desc, id desc'
        raise UserError(_('Removal strategy %s not implemented.') % (removal_strategy,))

    def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
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

        return self.search(domain, order=removal_strategy_order)

    @api.model
    def _get_available_quantity(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
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
        return sum(quants.mapped('quantity')) - sum(quants.mapped('reserved_quantity'))

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

        if lot_id:
            incoming_dates = quants.mapped('in_date')  # `mapped` already filtered out falsy items
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
                    # cleanup empty quants
                    if quant.quantity == 0 and quant.reserved_quantity == 0:
                        quant.unlink()
                    break
            except OperationalError, e:
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
        return self._get_available_quantity(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=False), fields.Datetime.from_string(in_date)

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
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)

        quants_quantity = sum(quants.mapped('quantity'))
        available_quantity = quants_quantity - sum(quants.mapped('reserved_quantity'))
        if quantity > 0 and quantity > available_quantity:
            raise UserError(_('It is not possible to reserve more products than you have in stock.'))
        elif quantity < 0 and abs(quantity) > sum(quants.mapped('reserved_quantity')):
            raise UserError(_('It is not possible to unreserve more products than you have in stock.'))

        reserved_quants = []
        for quant in quants:
            if quantity > 0:
                max_quantity_on_quant = quant.quantity - quant.reserved_quantity
                if max_quantity_on_quant <= 0:
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

            if quantity == 0 or available_quantity == 0:
                break
        return reserved_quants


class QuantPackage(models.Model):
    """ Packages containing quants and/or other packages """
    _name = "stock.quant.package"
    _description = "Physical Packages"
    _order = 'name'

    name = fields.Char(
        'Package Reference', copy=False, index=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('stock.quant.package') or _('Unknown Pack'))
    quant_ids = fields.One2many('stock.quant', 'package_id', 'Bulk Content', readonly=True)
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
    move_line_ids = fields.One2many('stock.move.line', 'result_package_id')
    current_picking_move_line_ids = fields.One2many('stock.move.line', compute="_compute_current_picking_info")
    current_picking_id = fields.Boolean(compute="_compute_current_picking_info")

    @api.depends('quant_ids.package_id', 'quant_ids.location_id', 'quant_ids.company_id', 'quant_ids.owner_id')
    def _compute_package_info(self):
        for package in self:
            values = {'location_id': False, 'company_id': self.env.user.company_id.id, 'owner_id': False}
            package.location_id = values['location_id']
            package.company_id = values['company_id']
            package.owner_id = values['owner_id']

    @api.multi
    def name_get(self):
        return list(self._compute_complete_name().items())

    def _compute_complete_name(self):
        """ Forms complete name of location from parent location to child location. """
        res = {}
        for package in self:
            name = package.name
            res[package.id] = name
        return res

    def _compute_current_picking_info(self):
        picking_id = self.env.context.get('picking_id')
        if picking_id:
            self.current_picking_move_line_ids = self.move_line_ids.filtered(lambda move_line: move_line.picking_id.id == picking_id)
            self.current_picking_id = True
        else:
            self.current_picking_move_line_ids = False
            self.current_picking_id = False


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
            locations = pack.get_content().filtered(lambda quant: quant.qty > 0.0).mapped('location_id')
            if len(locations) != 1:
                raise UserError(_('Everything inside a package should be in the same location'))
        return True

    @api.multi
    def unpack(self):
        for package in self:
            move_lines_to_remove = self.move_line_ids.filtered(lambda move_line: move_line.state != 'done')
            if move_lines_to_remove:
                move_lines_to_remove.write({'result_package_id': False})
            else:
                package.mapped('quant_ids').write({'package_id': False})

    def action_view_picking(self):
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        pickings = self.env['stock.move.line'].search([('result_package_id', 'in', self.ids)]).mapped('picking_id')
        action['domain'] = [('id', 'in', pickings.ids)]
        return action

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
