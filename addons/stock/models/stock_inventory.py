# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import float_compare, float_is_zero


class Inventory(models.Model):
    _name = "stock.inventory"
    _description = "Inventory"
    _order = "date desc, id desc"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        'Inventory Reference', default="Inventory",
        readonly=True, required=True,
        states={'draft': [('readonly', False)]})
    date = fields.Datetime(
        'Inventory Date',
        readonly=True, required=True,
        default=fields.Datetime.now,
        help="If the inventory adjustment is not validated, date at which the theoritical quantities have been checked.\n"
             "If the inventory adjustment is validated, date at which the inventory adjustment has been validated.")
    line_ids = fields.One2many(
        'stock.inventory.line', 'inventory_id', string='Inventories',
        copy=False, readonly=False,
        states={'done': [('readonly', True)]})
    move_ids = fields.One2many(
        'stock.move', 'inventory_id', string='Created Moves',
        states={'done': [('readonly', True)]})
    state = fields.Selection(string='Status', selection=[
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('confirm', 'In Progress'),
        ('done', 'Validated')],
        copy=False, index=True, readonly=True, tracking=True,
        default='draft')
    company_id = fields.Many2one(
        'res.company', 'Company',
        readonly=True, index=True, required=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env.company)
    location_ids = fields.Many2many(
        'stock.location', string='Locations',
        readonly=True, check_company=True,
        states={'draft': [('readonly', False)]},
        domain="[('company_id', '=', company_id), ('usage', 'in', ['internal', 'transit'])]")
    product_ids = fields.Many2many(
        'product.product', string='Products', check_company=True,
        domain="[('type', '=', 'product'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]", readonly=True,
        states={'draft': [('readonly', False)]},
        help="Specify Products to focus your inventory on particular Products.")
    start_empty = fields.Boolean('Empty Inventory',
        help="Allows to start with an empty inventory.")
    prefill_counted_quantity = fields.Selection(string='Counted Quantities',
        help="Allows to start with a pre-filled counted quantity for each lines or "
        "with all counted quantities set to zero.", default='counted',
        selection=[('counted', 'Default to stock on hand'), ('zero', 'Default to zero')])
    exhausted = fields.Boolean(
        'Include Exhausted Products', readonly=True,
        states={'draft': [('readonly', False)]},
        help="Include also products with quantity of 0")

    @api.onchange('company_id')
    def _onchange_company_id(self):
        # If the multilocation group is not active, default the location to the one of the main
        # warehouse.
        if not self.user_has_groups('stock.group_stock_multi_locations'):
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
            if warehouse:
                self.location_ids = warehouse.lot_stock_id

    def copy_data(self, default=None):
        name = _("%s (copy)") % (self.name)
        default = dict(default or {}, name=name)
        return super(Inventory, self).copy_data(default)

    def unlink(self):
        for inventory in self:
            if (inventory.state not in ('draft', 'cancel')
               and not self.env.context.get(MODULE_UNINSTALL_FLAG, False)):
                raise UserError(_('You can only delete a draft inventory adjustment. If the inventory adjustment is not done, you can cancel it.'))
        return super(Inventory, self).unlink()

    def action_validate(self):
        if not self.exists():
            return
        self.ensure_one()
        if not self.user_has_groups('stock.group_stock_manager'):
            raise UserError(_("Only a stock manager can validate an inventory adjustment."))
        if self.state != 'confirm':
            raise UserError(_(
                "You can't validate the inventory '%s', maybe this inventory "
                "has been already validated or isn't ready.", self.name))
        inventory_lines = self.line_ids.filtered(lambda l: l.product_id.tracking in ['lot', 'serial'] and not l.prod_lot_id and l.theoretical_qty != l.product_qty)
        lines = self.line_ids.filtered(lambda l: float_compare(l.product_qty, 1, precision_rounding=l.product_uom_id.rounding) > 0 and l.product_id.tracking == 'serial' and l.prod_lot_id)
        if inventory_lines and not lines:
            wiz_lines = [(0, 0, {'product_id': product.id, 'tracking': product.tracking}) for product in inventory_lines.mapped('product_id')]
            wiz = self.env['stock.track.confirmation'].create({'inventory_id': self.id, 'tracking_line_ids': wiz_lines})
            return {
                'name': _('Tracked Products in Inventory Adjustment'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'views': [(False, 'form')],
                'res_model': 'stock.track.confirmation',
                'target': 'new',
                'res_id': wiz.id,
            }
        self._action_done()
        self.line_ids._check_company()
        self._check_company()
        return True

    def _action_done(self):
        negative = next((line for line in self.mapped('line_ids') if line.product_qty < 0 and line.product_qty != line.theoretical_qty), False)
        if negative:
            raise UserError(_(
                'You cannot set a negative product quantity in an inventory line:\n\t%s - qty: %s',
                negative.product_id.display_name,
                negative.product_qty
            ))
        self.action_check()
        self.write({'state': 'done', 'date': fields.Datetime.now()})
        self.post_inventory()
        return True

    def post_inventory(self):
        # The inventory is posted as a single step which means quants cannot be moved from an internal location to another using an inventory
        # as they will be moved to inventory loss, and other quants will be created to the encoded quant location. This is a normal behavior
        # as quants cannot be reuse from inventory location (users can still manually move the products before/after the inventory if they want).
        self.mapped('move_ids').filtered(lambda move: move.state != 'done')._action_done()
        return True

    def action_check(self):
        """ Checks the inventory and computes the stock move to do """
        # tde todo: clean after _generate_moves
        for inventory in self.filtered(lambda x: x.state not in ('done','cancel')):
            # first remove the existing stock moves linked to this inventory
            inventory.with_context(prefetch_fields=False).mapped('move_ids').unlink()
            inventory.line_ids._generate_moves()

    def action_cancel_draft(self):
        self.mapped('move_ids')._action_cancel()
        self.line_ids.unlink()
        self.write({'state': 'draft'})

    def action_start(self):
        self.ensure_one()
        self._action_start()
        self._check_company()
        return self.action_open_inventory_lines()

    def _action_start(self):
        """ Confirms the Inventory Adjustment and generates its inventory lines
        if its state is draft and don't have already inventory lines (can happen
        with demo data or tests).
        """
        for inventory in self:
            if inventory.state != 'draft':
                continue
            vals = {
                'state': 'confirm',
                'date': fields.Datetime.now()
            }
            if not inventory.line_ids and not inventory.start_empty:
                self.env['stock.inventory.line'].create(inventory._get_inventory_lines_values())
            inventory.write(vals)

    def action_open_inventory_lines(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'name': _('Inventory Lines'),
            'res_model': 'stock.inventory.line',
        }
        context = {
            'default_is_editable': True,
            'default_inventory_id': self.id,
            'default_company_id': self.company_id.id,
        }
        # Define domains and context
        domain = [
            ('inventory_id', '=', self.id),
            ('location_id.usage', 'in', ['internal', 'transit'])
        ]
        if self.location_ids:
            context['default_location_id'] = self.location_ids[0].id
            if len(self.location_ids) == 1:
                if not self.location_ids[0].child_ids:
                    context['readonly_location_id'] = True

        if self.product_ids:
            # no_create on product_id field
            action['view_id'] = self.env.ref('stock.stock_inventory_line_tree_no_product_create').id
            if len(self.product_ids) == 1:
                context['default_product_id'] = self.product_ids[0].id
        else:
            # no product_ids => we're allowed to create new products in tree
            action['view_id'] = self.env.ref('stock.stock_inventory_line_tree').id

        action['context'] = context
        action['domain'] = domain
        return action

    def action_view_related_move_lines(self):
        self.ensure_one()
        domain = [('move_id', 'in', self.move_ids.ids)]
        action = {
            'name': _('Product Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move.line',
            'view_type': 'list',
            'view_mode': 'list,form',
            'domain': domain,
        }
        return action

    def action_print(self):
        return self.env.ref('stock.action_report_inventory').report_action(self)

    def _get_quantities(self):
        """Return quantities group by product_id, location_id, lot_id, package_id and owner_id

        :return: a dict with keys as tuple of group by and quantity as value
        :rtype: dict
        """
        self.ensure_one()
        if self.location_ids:
            domain_loc = [('id', 'child_of', self.location_ids.ids)]
        else:
            domain_loc = [('company_id', '=', self.company_id.id), ('usage', 'in', ['internal', 'transit'])]
        locations_ids = [l['id'] for l in self.env['stock.location'].search_read(domain_loc, ['id'])]

        domain = [('company_id', '=', self.company_id.id),
                  ('quantity', '!=', '0'),
                  ('location_id', 'in', locations_ids)]
        if self.prefill_counted_quantity == 'zero':
            domain.append(('product_id.active', '=', True))

        if self.product_ids:
            domain = expression.AND([domain, [('product_id', 'in', self.product_ids.ids)]])

        fields = ['product_id', 'location_id', 'lot_id', 'package_id', 'owner_id', 'quantity:sum']
        group_by = ['product_id', 'location_id', 'lot_id', 'package_id', 'owner_id']

        quants = self.env['stock.quant'].read_group(domain, fields, group_by, lazy=False)
        return {(
            quant['product_id'] and quant['product_id'][0] or False,
            quant['location_id'] and quant['location_id'][0] or False,
            quant['lot_id'] and quant['lot_id'][0] or False,
            quant['package_id'] and quant['package_id'][0] or False,
            quant['owner_id'] and quant['owner_id'][0] or False):
            quant['quantity'] for quant in quants
        }

    def _get_exhausted_inventory_lines_vals(self, non_exhausted_set):
        """Return the values of the inventory lines to create if the user
        wants to include exhausted products. Exhausted products are products
        without quantities or quantity equal to 0.

        :param non_exhausted_set: set of tuple (product_id, location_id) of non exhausted product-location
        :return: a list containing the `stock.inventory.line` values to create
        :rtype: list
        """
        self.ensure_one()
        if self.product_ids:
            product_ids = self.product_ids.ids
        else:
            product_ids = self.env['product.product'].search_read([
                '|', ('company_id', '=', self.company_id.id), ('company_id', '=', False),
                ('type', '=', 'product'),
                ('active', '=', True)], ['id'])
            product_ids = [p['id'] for p in product_ids]

        if self.location_ids:
            location_ids = self.location_ids.ids
        else:
            location_ids = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)]).lot_stock_id.ids

        vals = []
        for product_id in product_ids:
            for location_id in location_ids:
                if ((product_id, location_id) not in non_exhausted_set):
                    vals.append({
                        'inventory_id': self.id,
                        'product_id': product_id,
                        'location_id': location_id,
                        'theoretical_qty': 0
                    })
        return vals

    def _get_inventory_lines_values(self):
        """Return the values of the inventory lines to create for this inventory.

        :return: a list containing the `stock.inventory.line` values to create
        :rtype: list
        """
        self.ensure_one()
        quants_groups = self._get_quantities()
        vals = []
        for (product_id, location_id, lot_id, package_id, owner_id), quantity in quants_groups.items():
            line_values = {
                'inventory_id': self.id,
                'product_qty': 0 if self.prefill_counted_quantity == "zero" else quantity,
                'theoretical_qty': quantity,
                'prod_lot_id': lot_id,
                'partner_id': owner_id,
                'product_id': product_id,
                'location_id': location_id,
                'package_id': package_id
            }
            line_values['product_uom_id'] = self.env['product.product'].browse(product_id).uom_id.id
            vals.append(line_values)
        if self.exhausted:
            vals += self._get_exhausted_inventory_lines_vals({(l['product_id'], l['location_id']) for l in vals})
        return vals


class InventoryLine(models.Model):
    _name = "stock.inventory.line"
    _description = "Inventory Line"
    _order = "product_id, inventory_id, location_id, prod_lot_id"

    @api.model
    def _domain_location_id(self):
        if self.env.context.get('active_model') == 'stock.inventory':
            inventory = self.env['stock.inventory'].browse(self.env.context.get('active_id'))
            if inventory.exists() and inventory.location_ids:
                return "[('company_id', '=', company_id), ('usage', 'in', ['internal', 'transit']), ('id', 'child_of', %s)]" % inventory.location_ids.ids
        return "[('company_id', '=', company_id), ('usage', 'in', ['internal', 'transit'])]"

    @api.model
    def _domain_product_id(self):
        if self.env.context.get('active_model') == 'stock.inventory':
            inventory = self.env['stock.inventory'].browse(self.env.context.get('active_id'))
            if inventory.exists() and len(inventory.product_ids) > 1:
                return "[('type', '=', 'product'), '|', ('company_id', '=', False), ('company_id', '=', company_id), ('id', 'in', %s)]" % inventory.product_ids.ids
        return "[('type', '=', 'product'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]"

    is_editable = fields.Boolean(help="Technical field to restrict editing.")
    inventory_id = fields.Many2one(
        'stock.inventory', 'Inventory', check_company=True,
        index=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', 'Owner', check_company=True)
    product_id = fields.Many2one(
        'product.product', 'Product', check_company=True,
        domain=lambda self: self._domain_product_id(),
        index=True, required=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        required=True, readonly=True)
    product_qty = fields.Float(
        'Counted Quantity',
        readonly=True, states={'confirm': [('readonly', False)]},
        digits='Product Unit of Measure', default=0)
    categ_id = fields.Many2one(related='product_id.categ_id', store=True)
    location_id = fields.Many2one(
        'stock.location', 'Location', check_company=True,
        domain=lambda self: self._domain_location_id(),
        index=True, required=True)
    package_id = fields.Many2one(
        'stock.quant.package', 'Pack', index=True, check_company=True,
        domain="[('location_id', '=', location_id)]",
    )
    prod_lot_id = fields.Many2one(
        'stock.production.lot', 'Lot/Serial Number', check_company=True,
        domain="[('product_id','=',product_id), ('company_id', '=', company_id)]")
    company_id = fields.Many2one(
        'res.company', 'Company', related='inventory_id.company_id',
        index=True, readonly=True, store=True)
    state = fields.Selection(string='Status', related='inventory_id.state')
    theoretical_qty = fields.Float(
        'Theoretical Quantity',
        digits='Product Unit of Measure', readonly=True)
    difference_qty = fields.Float('Difference', compute='_compute_difference',
        help="Indicates the gap between the product's theoretical quantity and its newest quantity.",
        readonly=True, digits='Product Unit of Measure', search="_search_difference_qty")
    inventory_date = fields.Datetime('Inventory Date', readonly=True,
        default=fields.Datetime.now,
        help="Last date at which the On Hand Quantity has been computed.")
    outdated = fields.Boolean(string='Quantity outdated',
        compute='_compute_outdated', search='_search_outdated')
    product_tracking = fields.Selection(string='Tracking', related='product_id.tracking', readonly=True)

    @api.depends('product_qty', 'theoretical_qty')
    def _compute_difference(self):
        for line in self:
            line.difference_qty = line.product_qty - line.theoretical_qty

    @api.depends('inventory_date', 'product_id.stock_move_ids', 'theoretical_qty', 'product_uom_id.rounding')
    def _compute_outdated(self):
        quants_by_inventory = {inventory: inventory._get_quantities() for inventory in self.inventory_id}
        for line in self:
            quants = quants_by_inventory[line.inventory_id]
            if line.state == 'done' or not line.id:
                line.outdated = False
                continue
            qty = quants.get((
                line.product_id.id,
                line.location_id.id,
                line.prod_lot_id.id,
                line.package_id.id,
                line.partner_id.id), 0
            )
            if float_compare(qty, line.theoretical_qty, precision_rounding=line.product_uom_id.rounding) != 0:
                line.outdated = True
            else:
                line.outdated = False

    @api.onchange('product_id', 'location_id', 'product_uom_id', 'prod_lot_id', 'partner_id', 'package_id')
    def _onchange_quantity_context(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id
        if self.product_id and self.location_id and self.product_id.uom_id.category_id == self.product_uom_id.category_id:  # TDE FIXME: last part added because crash
            theoretical_qty = self.product_id.get_theoretical_quantity(
                self.product_id.id,
                self.location_id.id,
                lot_id=self.prod_lot_id.id,
                package_id=self.package_id.id,
                owner_id=self.partner_id.id,
                to_uom=self.product_uom_id.id,
            )
        else:
            theoretical_qty = 0
        # Sanity check on the lot.
        if self.prod_lot_id:
            if self.product_id.tracking == 'none' or self.product_id != self.prod_lot_id.product_id:
                self.prod_lot_id = False

        if self.prod_lot_id and self.product_id.tracking == 'serial':
            # We force `product_qty` to 1 for SN tracked product because it's
            # the only relevant value aside 0 for this kind of product.
            self.product_qty = 1
        elif self.product_id and float_compare(self.product_qty, self.theoretical_qty, precision_rounding=self.product_uom_id.rounding) == 0:
            # We update `product_qty` only if it equals to `theoretical_qty` to
            # avoid to reset quantity when user manually set it.
            self.product_qty = theoretical_qty
        self.theoretical_qty = theoretical_qty

    @api.model_create_multi
    def create(self, vals_list):
        """ Override to handle the case we create inventory line without
        `theoretical_qty` because this field is usually computed, but in some
        case (typicaly in tests), we create inventory line without trigger the
        onchange, so in this case, we set `theoretical_qty` depending of the
        product's theoretical quantity.
        Handles the same problem with `product_uom_id` as this field is normally
        set in an onchange of `product_id`.
        Finally, this override checks we don't try to create a duplicated line.
        """
        for values in vals_list:
            if 'theoretical_qty' not in values:
                theoretical_qty = self.env['product.product'].get_theoretical_quantity(
                    values['product_id'],
                    values['location_id'],
                    lot_id=values.get('prod_lot_id'),
                    package_id=values.get('package_id'),
                    owner_id=values.get('partner_id'),
                    to_uom=values.get('product_uom_id'),
                )
                values['theoretical_qty'] = theoretical_qty
            if 'product_id' in values and 'product_uom_id' not in values:
                values['product_uom_id'] = self.env['product.product'].browse(values['product_id']).uom_id.id
        res = super(InventoryLine, self).create(vals_list)
        res._check_no_duplicate_line()
        return res

    def write(self, vals):
        res = super(InventoryLine, self).write(vals)
        self._check_no_duplicate_line()
        return res

    def _check_no_duplicate_line(self):
        for line in self:
            domain = [
                ('id', '!=', line.id),
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', line.location_id.id),
                ('partner_id', '=', line.partner_id.id),
                ('package_id', '=', line.package_id.id),
                ('prod_lot_id', '=', line.prod_lot_id.id),
                ('inventory_id', '=', line.inventory_id.id)]
            existings = self.search_count(domain)
            if existings:
                raise UserError(_("There is already one inventory adjustment line for this product,"
                                  " you should rather modify this one instead of creating a new one."))

    @api.constrains('product_id')
    def _check_product_id(self):
        """ As no quants are created for consumable products, it should not be possible do adjust
        their quantity.
        """
        for line in self:
            if line.product_id.type != 'product':
                raise ValidationError(_("You can only adjust storable products.") + '\n\n%s -> %s' % (line.product_id.display_name, line.product_id.type))

    def _get_move_values(self, qty, location_id, location_dest_id, out):
        self.ensure_one()
        return {
            'name': _('INV:') + (self.inventory_id.name or ''),
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'product_uom_qty': qty,
            'date': self.inventory_id.date,
            'company_id': self.inventory_id.company_id.id,
            'inventory_id': self.inventory_id.id,
            'state': 'confirmed',
            'restrict_partner_id': self.partner_id.id,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'move_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'lot_id': self.prod_lot_id.id,
                'product_uom_qty': 0,  # bypass reservation here
                'product_uom_id': self.product_uom_id.id,
                'qty_done': qty,
                'package_id': out and self.package_id.id or False,
                'result_package_id': (not out) and self.package_id.id or False,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'owner_id': self.partner_id.id,
            })]
        }

    def _get_virtual_location(self):
        return self.product_id.with_company(self.company_id).property_stock_inventory

    def _generate_moves(self):
        vals_list = []
        for line in self:
            virtual_location = line._get_virtual_location()
            rounding = line.product_id.uom_id.rounding
            if float_is_zero(line.difference_qty, precision_rounding=rounding):
                continue
            if line.difference_qty > 0:  # found more than expected
                vals = line._get_move_values(line.difference_qty, virtual_location.id, line.location_id.id, False)
            else:
                vals = line._get_move_values(abs(line.difference_qty), line.location_id.id, virtual_location.id, True)
            vals_list.append(vals)
        return self.env['stock.move'].create(vals_list)

    def action_refresh_quantity(self):
        filtered_lines = self.filtered(lambda l: l.state != 'done')
        for line in filtered_lines:
            if line.outdated:
                quants = self.env['stock.quant']._gather(line.product_id, line.location_id, lot_id=line.prod_lot_id, package_id=line.package_id, owner_id=line.partner_id, strict=True)
                if quants.exists():
                    quantity = sum(quants.mapped('quantity'))
                    if line.theoretical_qty != quantity:
                        line.theoretical_qty = quantity
                else:
                    line.theoretical_qty = 0
                line.inventory_date = fields.Datetime.now()

    def action_reset_product_qty(self):
        """ Write `product_qty` to zero on the selected records. """
        impacted_lines = self.env['stock.inventory.line']
        for line in self:
            if line.state == 'done':
                continue
            impacted_lines |= line
        impacted_lines.write({'product_qty': 0})

    def _search_difference_qty(self, operator, value):
        if operator == '=':
            result = True
        elif operator == '!=':
            result = False
        else:
            raise NotImplementedError()
        lines = self.search([('inventory_id', '=', self.env.context.get('default_inventory_id'))])
        line_ids = lines.filtered(lambda line: float_is_zero(line.difference_qty, line.product_id.uom_id.rounding) == result).ids
        return [('id', 'in', line_ids)]

    def _search_outdated(self, operator, value):
        if operator != '=':
            if operator == '!=' and isinstance(value, bool):
                value = not value
            else:
                raise NotImplementedError()
        lines = self.search([('inventory_id', '=', self.env.context.get('default_inventory_id'))])
        line_ids = lines.filtered(lambda line: line.outdated == value).ids
        return [('id', 'in', line_ids)]
