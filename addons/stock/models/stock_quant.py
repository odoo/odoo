# Part of Odoo. See LICENSE file for full copyright and licensing details.
import heapq
import logging
from collections import namedtuple

from ast import literal_eval
from collections import defaultdict
from markupsafe import escape
from psycopg2 import Error

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.osv import expression
from odoo.tools import SQL, check_barcode_encoding, groupby
from odoo.tools.float_utils import float_compare, float_is_zero

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _name = 'stock.quant'
    _description = 'Quants'
    _rec_name = 'product_id'
    _rec_names_search = ['location_id', 'lot_id', 'package_id', 'owner_id']

    def _domain_location_id(self):
        if self.env.user.has_group('stock.group_stock_user'):
            return "[('usage', 'in', ['internal', 'transit'])] if context.get('inventory_mode') else []"
        return "[]"

    def _domain_lot_id(self):
        if self.env.user.has_group('stock.group_stock_user'):
            return ("[] if not context.get('inventory_mode') else"
                " [('product_id', '=', context.get('active_id', False))] if context.get('active_model') == 'product.product' else"
                " [('product_id.product_tmpl_id', '=', context.get('active_id', False))] if context.get('active_model') == 'product.template' else"
                " [('product_id', '=', product_id)]")
        return "[]"

    def _domain_product_id(self):
        if self.env.user.has_group('stock.group_stock_user'):
            return ("[] if not context.get('inventory_mode') else"
                " [('is_storable', '=', True), ('product_tmpl_id', 'in', context.get('product_tmpl_ids', []) + [context.get('product_tmpl_id', 0)])] if context.get('product_tmpl_ids') or context.get('product_tmpl_id') else"
                " [('is_storable', '=', True)]")
        return "[]"

    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=lambda self: self._domain_product_id(),
        ondelete='restrict', required=True, index=True, check_company=True)
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product Template',
        related='product_id.product_tmpl_id')
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit',
        readonly=True, related='product_id.uom_id')
    is_favorite = fields.Boolean(related='product_tmpl_id.is_favorite')
    company_id = fields.Many2one(related='location_id.company_id', string='Company', store=True, readonly=True)
    location_id = fields.Many2one(
        'stock.location', 'Location',
        domain=lambda self: self._domain_location_id(),
        auto_join=True, ondelete='restrict', required=True, index=True)
    warehouse_id = fields.Many2one('stock.warehouse', related='location_id.warehouse_id')
    storage_category_id = fields.Many2one(related='location_id.storage_category_id')
    cyclic_inventory_frequency = fields.Integer(related='location_id.cyclic_inventory_frequency')
    lot_id = fields.Many2one(
        'stock.lot', 'Lot/Serial Number', index=True,
        ondelete='restrict', check_company=True,
        domain=lambda self: self._domain_lot_id())
    lot_properties = fields.Properties(related='lot_id.lot_properties', definition='product_id.lot_properties_definition', readonly=True)
    sn_duplicated = fields.Boolean(string="Duplicated Serial Number", compute='_compute_sn_duplicated', help="If the same SN is in another Quant")
    package_id = fields.Many2one(
        'stock.quant.package', 'Package',
        domain="['|', ('location_id', '=', location_id), '&', ('location_id', '=', False), '&', ('package_use', '=', 'reusable'), ('quant_ids', '=', False)]",
        help='The package containing this quant', ondelete='restrict', check_company=True, index=True)
    owner_id = fields.Many2one(
        'res.partner', 'Owner',
        help='This is the owner of the quant', check_company=True,
        index='btree_not_null')
    quantity = fields.Float(
        'Quantity',
        help='Quantity of products in this quant, in the default unit of measure of the product',
        readonly=True, digits='Product Unit')
    reserved_quantity = fields.Float(
        'Reserved Quantity',
        default=0.0,
        help='Quantity of reserved products in this quant, in the default unit of measure of the product',
        readonly=True, required=True, digits='Product Unit')
    available_quantity = fields.Float(
        'Available Quantity',
        help="On hand quantity which hasn't been reserved on a transfer, in the default unit of measure of the product",
        compute='_compute_available_quantity', digits='Product Unit')
    in_date = fields.Datetime('Incoming Date', readonly=True, required=True, default=fields.Datetime.now)
    tracking = fields.Selection(related='product_id.tracking', readonly=True)
    on_hand = fields.Boolean('On Hand', store=False, search='_search_on_hand')
    product_categ_id = fields.Many2one(related='product_tmpl_id.categ_id')

    # Inventory Fields
    inventory_quantity = fields.Float(
        'Counted Quantity', digits='Product Unit',
        help="The product's counted quantity.")
    inventory_quantity_auto_apply = fields.Float(
        'Inventoried Quantity', digits='Product Unit',
        compute='_compute_inventory_quantity_auto_apply',
        inverse='_set_inventory_quantity', groups='stock.group_stock_manager'
    )
    inventory_diff_quantity = fields.Float(
        'Difference', compute='_compute_inventory_diff_quantity', store=True,
        help="Indicates the gap between the product's theoretical quantity and its counted quantity.",
        readonly=True, digits='Product Unit')
    inventory_date = fields.Date(
        'Scheduled Date', compute='_compute_inventory_date', store=True, readonly=False,
        help="Next date the On Hand Quantity should be counted.")
    last_count_date = fields.Date(compute='_compute_last_count_date', help='Last time the Quantity was Updated')
    inventory_quantity_set = fields.Boolean(store=True, compute='_compute_inventory_quantity_set', readonly=False)
    is_outdated = fields.Boolean('Quantity has been moved since last count', compute='_compute_is_outdated', search='_search_is_outdated')
    user_id = fields.Many2one(
        'res.users', 'Assigned To', help="User assigned to do product count.",
        domain=lambda self: [('all_group_ids', 'in', self.env.ref('stock.group_stock_user').id)])

    @api.depends('quantity', 'reserved_quantity')
    def _compute_available_quantity(self):
        for quant in self:
            quant.available_quantity = quant.quantity - quant.reserved_quantity

    @api.depends('location_id')
    def _compute_inventory_date(self):
        quants = self.filtered(lambda q: not q.inventory_date and q.location_id.usage in ['internal', 'transit'])
        date_by_location = {loc: loc._get_next_inventory_date() for loc in quants.location_id}
        for quant in quants:
            quant.inventory_date = date_by_location[quant.location_id]

    def _compute_last_count_date(self):
        """ We look at the stock move lines associated with every quant to get the last count date.
        """
        self.last_count_date = False
        groups = self.env['stock.move.line']._read_group(
            [
                ('state', '=', 'done'),
                ('is_inventory', '=', True),
                ('product_id', 'in', self.product_id.ids),
                '|',
                    ('lot_id', 'in', self.lot_id.ids),
                    ('lot_id', '=', False),
                '|',
                    ('owner_id', 'in', self.owner_id.ids),
                    ('owner_id', '=', False),
                '|',
                    ('location_id', 'in', self.location_id.ids),
                    ('location_dest_id', 'in', self.location_id.ids),
                '|',
                    ('package_id', '=', False),
                    '|',
                        ('package_id', 'in', self.package_id.ids),
                        ('result_package_id', 'in', self.package_id.ids),
            ],
            ['product_id', 'lot_id', 'package_id', 'owner_id', 'result_package_id', 'location_id', 'location_dest_id'],
            ['date:max'])

        def _update_dict(date_by_quant, key, value):
            current_date = date_by_quant.get(key)
            if not current_date or value > current_date:
                date_by_quant[key] = value

        date_by_quant = {}
        for product, lot, package, owner, result_package, location, location_dest, move_line_date in groups:
            location_id = location.id
            location_dest_id = location_dest.id
            package_id = package.id
            result_package_id = result_package.id
            lot_id = lot.id
            owner_id = owner.id
            product_id = product.id
            _update_dict(date_by_quant, (location_id, package_id, product_id, lot_id, owner_id), move_line_date)
            _update_dict(date_by_quant, (location_dest_id, package_id, product_id, lot_id, owner_id), move_line_date)
            _update_dict(date_by_quant, (location_id, result_package_id, product_id, lot_id, owner_id), move_line_date)
            _update_dict(date_by_quant, (location_dest_id, result_package_id, product_id, lot_id, owner_id), move_line_date)
        for quant in self:
            quant.last_count_date = date_by_quant.get((quant.location_id.id, quant.package_id.id, quant.product_id.id, quant.lot_id.id, quant.owner_id.id))

    def _search(self, domain, *args, **kwargs):
        domain = Domain(domain).map_conditions(
            lambda condition: Domain('lot_id', 'any', [condition]) if condition.field_expr.startswith('lot_properties.') else condition
        )
        return super()._search(domain, *args, **kwargs)

    @api.depends('inventory_quantity', 'inventory_quantity_set')
    def _compute_inventory_diff_quantity(self):
        for quant in self:
            if quant.inventory_quantity_set:
                quant.inventory_diff_quantity = quant.inventory_quantity - quant.quantity
            else:
                quant.inventory_diff_quantity = 0

    @api.depends('inventory_quantity')
    def _compute_inventory_quantity_set(self):
        self.inventory_quantity_set = True

    @api.depends('inventory_quantity', 'quantity', 'product_id')
    def _compute_is_outdated(self):
        self.is_outdated = False
        for quant in self:
            if quant.product_id and float_compare(quant.inventory_quantity - quant.inventory_diff_quantity, quant.quantity, precision_rounding=quant.product_uom_id.rounding) and quant.inventory_quantity_set:
                quant.is_outdated = True

    def _search_is_outdated(self, operator, value):
        if operator != 'in':
            return NotImplemented
        quant_ids = self.search([('inventory_quantity_set', '=', True)])
        quant_ids = quant_ids.filtered(lambda quant: float_compare(quant.inventory_quantity - quant.inventory_diff_quantity, quant.quantity, precision_rounding=quant.product_uom_id.rounding)).ids
        return [('id', 'in', quant_ids)]

    @api.depends('quantity')
    def _compute_inventory_quantity_auto_apply(self):
        for quant in self:
            quant.inventory_quantity_auto_apply = quant.quantity

    @api.depends('lot_id')
    def _compute_sn_duplicated(self):
        self.sn_duplicated = False
        domain = [('tracking', '=', 'serial'), ('lot_id', 'in', self.lot_id.ids), ('location_id.usage', 'in', ['internal', 'transit'])]
        results = self._read_group(domain, ['lot_id'], having=[('__count', '>', 1)])
        duplicated_sn_ids = [lot.id for [lot] in results]
        quants_with_duplicated_sn = self.env['stock.quant'].search([('lot_id', 'in', duplicated_sn_ids)])
        quants_with_duplicated_sn.sn_duplicated = True

    def _set_inventory_quantity(self):
        """ Inverse method to create stock move when `inventory_quantity` is set
        (`inventory_quantity` is only accessible in inventory mode).
        """
        if not self._is_inventory_mode():
            return
        quant_to_inventory = self.env['stock.quant']
        for quant in self:
            if quant.quantity == quant.inventory_quantity_auto_apply:
                continue
            quant.inventory_quantity = quant.inventory_quantity_auto_apply
            quant_to_inventory |= quant
        quant_to_inventory.action_apply_inventory()

    def _search_on_hand(self, operator, value):
        """Handle the "on_hand" filter, indirectly calling `_get_domain_locations`."""
        if operator != 'in':
            return NotImplemented
        return self.env['product.product']._get_domain_locations()[0]

    def copy(self, default=None):
        raise UserError(_('You cannot duplicate stock quants.'))

    @api.model
    def name_create(self, name):
        return False

    @api.model_create_multi
    def create(self, vals_list):
        """ Override to handle the "inventory mode" and create a quant as
        superuser the conditions are met.
        """
        def _add_to_cache(quant):
            if 'quants_cache' in self.env.context:
                self.env.context['quants_cache'][
                    quant.product_id.id, quant.location_id.id, quant.lot_id.id, quant.package_id.id, quant.owner_id.id
                ] |= quant

        quants = self.env['stock.quant']
        is_inventory_mode = self._is_inventory_mode()
        allowed_fields = self._get_inventory_fields_create()
        for vals in vals_list:
            if is_inventory_mode and any(f in vals for f in ['inventory_quantity', 'inventory_quantity_auto_apply']):
                if any(field for field in vals.keys() if field not in allowed_fields):
                    raise UserError(_("Quant's creation is restricted, you can't do this operation."))
                auto_apply = 'inventory_quantity_auto_apply' in vals
                inventory_quantity = vals.pop('inventory_quantity_auto_apply', False) or vals.pop(
                    'inventory_quantity', False) or 0
                # Create an empty quant or write on a similar one.
                product = self.env['product.product'].browse(vals['product_id'])
                location = self.env['stock.location'].browse(vals['location_id'])
                lot_id = self.env['stock.lot'].browse(vals.get('lot_id'))
                package_id = self.env['stock.quant.package'].browse(vals.get('package_id'))
                owner_id = self.env['res.partner'].browse(vals.get('owner_id'))
                quant = self.env['stock.quant']
                if not self.env.context.get('import_file'):
                    # Merge quants later, to make sure one line = one record during batch import
                    quant = self._gather(product, location, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True)
                if lot_id:
                    if self.env.context.get('import_file') and lot_id.product_id != product:
                        lot_name = lot_id.name
                        lot_id = self.env['stock.lot'].search([('product_id', '=', product.id), ('name', '=', lot_name)], limit=1)
                        if not lot_id:
                            company_id = location.company_id or self.env.company
                            lot_id = self.env['stock.lot'].create({'name': lot_name, 'product_id': product.id, 'company_id': company_id.id})
                        vals['lot_id'] = lot_id.id
                    quant = quant.filtered(lambda q: q.lot_id)
                if quant:
                    quant = quant[0].sudo()
                else:
                    quant = self.sudo().create(vals)
                    _add_to_cache(quant)
                if auto_apply:
                    quant.write({'inventory_quantity_auto_apply': inventory_quantity})
                else:
                    # Set the `inventory_quantity` field to create the necessary move.
                    quant.inventory_quantity = inventory_quantity
                    quant.user_id = vals.get('user_id', self.env.user.id)
                    quant.inventory_date = fields.Date.today()
                quants |= quant
            else:
                if 'inventory_quantity' not in vals:
                    vals['inventory_quantity_set'] = vals.get('inventory_quantity_set', False)
                quant = super().create(vals)
                _add_to_cache(quant)
                quants |= quant
                if self._is_inventory_mode() and quant.company_id:
                    quant._check_company()
        return quants

    def _load_records_create(self, values):
        """ Add default location if import file did not fill it"""
        company_user = self.env.company
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
        for value in values:
            if 'location_id' not in value:
                value['location_id'] = warehouse.lot_stock_id.id
        return super(StockQuant, self.with_context(inventory_mode=True))._load_records_create(values)

    def _load_records_write(self, values):
        """ Only allowed fields should be modified """
        return super(StockQuant, self.with_context(inventory_mode=True))._load_records_write(values)

    def _read_group_select(self, aggregate_spec, query):
        if aggregate_spec == 'inventory_quantity:sum' and self.env.context.get('inventory_report_mode'):
            return SQL("NULL")
        if aggregate_spec == 'available_quantity:sum':
            sql_quantity = self._read_group_select('quantity:sum', query)
            sql_reserved_quantity = self._read_group_select('reserved_quantity:sum', query)
            return SQL("%s - %s", sql_quantity, sql_reserved_quantity)
        if aggregate_spec == 'inventory_quantity_auto_apply:sum':
            return self._read_group_select('quantity:sum', query)
        return super()._read_group_select(aggregate_spec, query)

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Inventory Adjustments'),
            'template': '/stock/static/xlsx/stock_quant.xlsx'
        }]

    @api.model
    def _get_forbidden_fields_write(self):
        """ Returns a list of fields user can't edit when he want to edit a quant in `inventory_mode`."""
        return ['product_id', 'location_id', 'lot_id', 'package_id', 'owner_id']

    def write(self, vals):
        """ Override to handle the "inventory mode" and create the inventory move. """
        forbidden_fields = self._get_forbidden_fields_write()
        if self._is_inventory_mode() and any(field for field in forbidden_fields if field in vals.keys()):
            if any(quant.location_id.usage == 'inventory' for quant in self):
                # Do nothing when user tries to modify manually a inventory loss
                return
            self = self.sudo()
            raise UserError(_("Quant's editing is restricted, you can't do this operation."))
        return super(StockQuant, self).write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_wrong_permission(self):
        if not self.env.is_superuser():
            if not self.env.user.has_group('stock.group_stock_manager'):
                raise UserError(_("Quants are auto-deleted when appropriate. If you must manually delete them, please ask a stock manager to do it."))
            self = self.with_context(inventory_mode=True)
            self.inventory_quantity = 0
            self._apply_inventory()

    def action_view_stock_moves(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.stock_move_line_action")
        action['domain'] = [
            '|',
                ('location_id', '=', self.location_id.id),
                ('location_dest_id', '=', self.location_id.id),
            ('lot_id', '=', self.lot_id.id),
        ]
        if self.package_id:
            action['domain'] += [
                '|',
                    ('package_id', '=', self.package_id.id),
                    ('result_package_id', '=', self.package_id.id),
            ]
        action['context'] = literal_eval(action.get('context'))
        action['context']['search_default_product_id'] = self.product_id.id
        return action

    def action_view_orderpoints(self):
        action = self.env['product.product'].action_view_orderpoints()
        action['domain'] = [('product_id', '=', self.product_id.id)]
        return action

    @api.model
    def action_view_quants(self):
        self = self.with_context(search_default_internal_loc=1)
        self = self._set_view_context()
        return self._get_quants_action(extend=True)

    @api.model
    def action_view_inventory(self):
        """ Similar to _get_quants_action except specific for inventory adjustments (i.e. inventory counts). """
        self = self._set_view_context()
        if not self.env['ir.config_parameter'].sudo().get_param('stock.skip_quant_tasks'):
            self._quant_tasks()

        ctx = dict(self.env.context or {})
        ctx['no_at_date'] = True
        if self.env.user.has_group('stock.group_stock_user') and not self.env.user.has_group('stock.group_stock_manager'):
            ctx['search_default_my_count'] = True
        view_id = self.env.ref('stock.view_stock_quant_tree_inventory_editable').id
        action = {
            'name': _('Inventory Adjustments'),
            'view_mode': 'list',
            'res_model': 'stock.quant',
            'type': 'ir.actions.act_window',
            'context': ctx,
            'domain': [('location_id.usage', 'in', ['internal', 'transit'])],
            'views': [(view_id, 'list')],
            'help': """
                <p class="o_view_nocontent_smiling_face">
                    {}
                </p>
                <p>
                    {} <span class="fa fa-cog"/>
                </p>
                """.format(escape(_('Your stock is currently empty')),
                           escape(_('Press the "New" button to define the quantity for a product in your stock or import quantities from a spreadsheet via the Actions menu'))),
        }
        return action

    def action_apply_inventory(self):
        # for some reason if multi-record, env.context doesn't pass to wizards...
        ctx = dict(self.env.context or {})
        ctx['default_quant_ids'] = self.ids
        quants_outdated = self.filtered(lambda quant: quant.is_outdated)
        if quants_outdated:
            ctx['default_quant_to_fix_ids'] = quants_outdated.ids
            return {
                'name': _('Conflict in Inventory Adjustment'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'views': [(False, 'form')],
                'res_model': 'stock.inventory.conflict',
                'target': 'new',
                'context': ctx,
            }
        self._apply_inventory()
        self.inventory_quantity_set = False

    def action_stock_quant_relocate(self):
        if len(self.company_id) > 1 or any(not q.company_id.id for q in self) or any(q <= 0 for q in self.mapped('quantity')):
            raise UserError(_('You can only move positive quantities stored in locations used by a single company per relocation.'))
        context = {
            'default_quant_ids': self.ids,
            'default_lot_id': self.env.context.get("default_lot_id", False),
            'single_product': self.env.context.get("single_product", False)
        }
        return {
            'res_model': 'stock.quant.relocate',
            'views': [[False, 'form']],
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': context,
        }

    def action_inventory_history(self):
        self.ensure_one()
        action = {
            'name': _('History'),
            'view_mode': 'list,form',
            'res_model': 'stock.move.line',
            'views': [(self.env.ref('stock.view_move_line_tree').id, 'list'), (False, 'form')],
            'type': 'ir.actions.act_window',
            'context': {
                'search_default_inventory': 1,
                'search_default_done': 1,
                'search_default_product_id': self.product_id.id,
            },
            'domain': [
                ('company_id', '=', self.company_id.id),
                '|',
                    ('location_id', '=', self.location_id.id),
                    ('location_dest_id', '=', self.location_id.id),
            ],
        }
        if self.lot_id:
            action['context']['search_default_lot_id'] = self.lot_id.id
        if self.package_id:
            action['context']['search_default_package_id'] = self.package_id.id
            action['context']['search_default_result_package_id'] = self.package_id.id
        if self.owner_id:
            action['context']['search_default_owner_id'] = self.owner_id.id
        return action

    def action_set_inventory_quantity(self):
        quants_already_set = self.filtered(lambda quant: quant.inventory_quantity_set)
        if quants_already_set:
            ctx = dict(self.env.context or {}, default_quant_ids=self.ids)
            view = self.env.ref('stock.inventory_warning_set_view', False)
            return {
                'name': _('Quantities Already Set'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'res_model': 'stock.inventory.warning',
                'target': 'new',
                'context': ctx,
            }
        for quant in self:
            quant.inventory_quantity = quant.quantity
        self.user_id = self.env.user.id
        self.inventory_quantity_set = True

    def action_apply_all(self):
        quant_ids = self.env['stock.quant'].search(self.env.context['active_domain']).ids
        ctx = dict(self.env.context or {}, default_quant_ids=quant_ids)
        view = self.env.ref('stock.stock_inventory_adjustment_name_form_view', False)
        return {
            'name': _('Inventory Adjustment Reference / Reason'),
            'type': 'ir.actions.act_window',
            'views': [(view.id, 'form')],
            'res_model': 'stock.inventory.adjustment.name',
            'target': 'new',
            'context': ctx,
        }

    def action_reset(self):
        ctx = dict(self.env.context or {}, default_quant_ids=self.ids)
        view = self.env.ref('stock.inventory_warning_reset_view', False)
        return {
            'name': _('Quantities To Reset'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'res_model': 'stock.inventory.warning',
            'target': 'new',
            'context': ctx,
        }

    def action_clear_inventory_quantity(self):
        self.inventory_quantity = 0
        self.inventory_diff_quantity = 0
        self.inventory_quantity_set = False
        self.user_id = False

    def action_set_inventory_quantity_zero(self):
        self.filtered(lambda l: not l.inventory_quantity).inventory_quantity = 0
        self.user_id = self.env.user.id

    def action_warning_duplicated_sn(self):
        return {
            'name': _('Warning Duplicated SN'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.quant',
            'views': [(self.env.ref('stock.duplicated_sn_warning').id, 'form')],
            'target': 'new',
        }

    @api.depends('location_id', 'lot_id', 'package_id', 'owner_id')
    def _compute_display_name(self):
        """name that will be displayed in the detailed operation"""
        for record in self:
            if record.env.context.get('formatted_display_name'):
                name = f"{record.location_id.name}"
                if record.package_id:
                    name += f"\t--{record.package_id.name}--"
                if record.lot_id:
                    name += (' ' if record.package_id else '\t') + f"--{record.lot_id.name}--"
                record.display_name = name
            else:
                name = [record.location_id.display_name]
                if record.lot_id:
                    name.append(record.lot_id.name)
                if record.package_id:
                    name.append(record.package_id.name)
                if record.owner_id:
                    name.append(record.owner_id.name)
                record.display_name = ' - '.join(name)

    @api.constrains('product_id')
    def check_product_id(self):
        if any(not elem.product_id.is_storable for elem in self):
            raise ValidationError(_('Quants cannot be created for consumables or services.'))

    def check_quantity(self):
        sn_quants = self.filtered(lambda q: q.product_id.tracking == 'serial' and q.location_id.usage != 'inventory' and q.lot_id)
        if not sn_quants:
            return
        domain = [
            ('product_id', 'in', sn_quants.product_id.ids),
            ('location_id', 'child_of', sn_quants.location_id.ids),
            ('lot_id', 'in', sn_quants.lot_id.ids)
        ]
        groups = self._read_group(
            domain,
            ['product_id', 'location_id', 'lot_id'],
            ['quantity:sum'],
        )
        for product, _location, lot, qty in groups:
            if float_compare(abs(qty), 1, precision_rounding=product.uom_id.rounding) > 0:
                raise ValidationError(_('The serial number has already been assigned: \n Product: %(product)s, Serial Number: %(serial_number)s', product=product.display_name, serial_number=lot.name))

    @api.constrains('location_id')
    def check_location_id(self):
        for quant in self:
            if quant.location_id.usage == 'view':
                raise ValidationError(_('You cannot take products from or deliver products to a location of type "view" (%s).', quant.location_id.name))

    @api.constrains('lot_id')
    def check_lot_id(self):
        for quant in self:
            if quant.lot_id.product_id and quant.lot_id.product_id != quant.product_id:
                raise ValidationError(_('The Lot/Serial number (%s) is linked to another product.', quant.lot_id.name))

    @api.model
    def _get_removal_strategy(self, product_id, location_id):
        product_id = product_id.sudo()
        location_id = location_id.sudo()
        if product_id.categ_id.removal_strategy_id:
            return product_id.categ_id.removal_strategy_id.with_context(lang=None).method
        loc = location_id
        while loc:
            if loc.removal_strategy_id:
                return loc.removal_strategy_id.with_context(lang=None).method
            loc = loc.location_id
        return 'fifo'

    def _run_least_packages_removal_strategy_astar(self, domain, qty):
        # Fetch the available packages and contents
        query = self._where_calc(domain)
        query.groupby = SQL("package_id")
        query.having = SQL("SUM(quantity - reserved_quantity) > 0")
        query.order = SQL("available_qty DESC")
        qty_by_package = self.env.execute_query(
            query.select('package_id', 'SUM(quantity - reserved_quantity) AS available_qty'))

        # Items that do not belong to a package are added individually to the list, any empty packages get removed.
        pkg_found = False
        new_qty_by_package = []
        none_elements = []

        for elem in qty_by_package:
            if elem[0] is None:
                none_elements.extend([(None, 1) for _ in range(int(elem[1]))])
            elif elem[1] != 0:
                new_qty_by_package.append(elem)
                pkg_found = True

        new_qty_by_package.extend(none_elements)
        qty_by_package = new_qty_by_package

        if not pkg_found:
            return domain
        size = len(qty_by_package)

        class PriorityQueue:
            def __init__(self):
                self.elements = []

            def empty(self) -> bool:
                return not self.elements

            def put(self, item, priority):
                heapq.heappush(self.elements, (priority, item))

            def get(self):
                return heapq.heappop(self.elements)[1]

        def heuristic(node):
            if node.next_index < size:
                return len(node.taken_packages) + node.count_remaining / qty_by_package[node.next_index][1]
            return len(node.taken_packages)

        def generate_domain(node):
            selected_single_items = []
            single_item_ids = False
            for pkg in node.taken_packages:
                if pkg[0] is None:
                    # Lazily retrieve ids for single items
                    if not single_item_ids:
                        single_item_ids = self.search(expression.AND([[('package_id', '=', None)], domain])).ids
                    selected_single_items.append(single_item_ids.pop())

            expr = [('package_id', 'in', [elem[0] for elem in node.taken_packages if elem[0] is not None])]
            if selected_single_items:
                expr = expression.OR([expr, [('id', 'in', selected_single_items)]])
            return expression.AND([expr, domain])

        Node = namedtuple("Node", "count_remaining taken_packages next_index")

        frontier = PriorityQueue()
        frontier.put(Node(qty, (), 0), 0)

        best_leaf = Node(qty, (), 0)

        try:
            while not frontier.empty():
                current = frontier.get()

                if current.count_remaining <= 0:
                    return generate_domain(current)

                # Keep track of processed package amounts to only generate one branch for the same amount
                last_count = None
                i = current.next_index
                while i < size:
                    pkg = qty_by_package[i]
                    i += 1
                    if pkg[1] == last_count:
                        continue
                    last_count = pkg[1]

                    count = current.count_remaining - pkg[1]
                    taken = current.taken_packages + (pkg,)
                    node = Node(count, taken, i)

                    if count < 0:
                        # Overselect case
                        if best_leaf.count_remaining > 0 or len(node.taken_packages) < len(best_leaf.taken_packages) or (len(node.taken_packages) == len(best_leaf.taken_packages) and node.count_remaining > best_leaf.count_remaining):
                            best_leaf = node
                        continue

                    if i >= size and count != 0:
                        # Not enough packages case
                        if node.count_remaining < best_leaf.count_remaining:
                            best_leaf = node
                        continue

                    frontier.put(node, heuristic(node))
        except MemoryError:
            _logger.info('Ran out of memory while trying to use the least_packages strategy to get quants. Domain: %s', domain)
            return domain

        # no exact matching possible, use best leaf
        return generate_domain(best_leaf)

    @api.model
    def _get_removal_strategy_order(self, removal_strategy):
        if removal_strategy in ['fifo', 'least_packages']:
            return 'in_date ASC, id'
        elif removal_strategy == 'lifo':
            return 'in_date DESC, id DESC'
        elif removal_strategy == 'closest':
            return False
        raise UserError(_('Removal strategy %s not implemented.', removal_strategy))

    def _get_gather_domain(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        domain = [('product_id', '=', product_id.id)]
        if not strict:
            if lot_id:
                domain = expression.AND([['|', ('lot_id', '=', lot_id.id), ('lot_id', '=', False)], domain])
            if package_id:
                domain = expression.AND([[('package_id', '=', package_id.id)], domain])
            if owner_id:
                domain = expression.AND([[('owner_id', '=', owner_id.id)], domain])
            domain = expression.AND([[('location_id', 'child_of', location_id.id)], domain])
        else:
            domain = expression.AND([['|', ('lot_id', '=', lot_id.id), ('lot_id', '=', False)] if lot_id else [('lot_id', '=', False)], domain])
            domain = expression.AND([[('package_id', '=', package_id and package_id.id or False)], domain])
            domain = expression.AND([[('owner_id', '=', owner_id and owner_id.id or False)], domain])
            domain = expression.AND([[('location_id', '=', location_id.id)], domain])
        if self.env.context.get('with_expiration'):
            domain = expression.AND([['|', ('expiration_date', '>=', self.env.context['with_expiration']), ('expiration_date', '=', False)], domain])
        return domain

    def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, qty=0):
        """ if records in self, the records are filtered based on the wanted characteristics passed to this function
            if not, a search is done with all the characteristics passed.
        """
        removal_strategy = self._get_removal_strategy(product_id, location_id)
        domain = self._get_gather_domain(product_id, location_id, lot_id, package_id, owner_id, strict)
        if removal_strategy == 'least_packages' and qty:
            domain = self._run_least_packages_removal_strategy_astar(domain, qty)
        order = self._get_removal_strategy_order(removal_strategy)

        quants_cache = self.env.context.get('quants_cache')
        if quants_cache is not None and strict and removal_strategy != 'least_packages':
            res = self.env['stock.quant']
            if lot_id:
                res |= quants_cache[product_id.id, location_id.id, lot_id.id, package_id.id, owner_id.id]
            res |= quants_cache[product_id.id, location_id.id, False, package_id.id, owner_id.id]
        else:
            res = self.search(domain, order=order)
        if removal_strategy == "closest":
            res = res.sorted(lambda q: (q.location_id.complete_name, -q.id))
        return res.sorted(lambda q: not q.lot_id)

    def _get_available_quantity(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, allow_negative=False):
        """ Return the available quantity, i.e. the sum of `quantity` minus the sum of
        `reserved_quantity`, for the set of quants sharing the combination of `product_id,
        location_id` if `strict` is set to False or sharing the *exact same characteristics*
        otherwise.
        The set of quants to filter from can be in `self`, if not a search will be done
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
                if not quant.lot_id and strict and lot_id:
                    continue
                if not quant.lot_id:
                    availaible_quantities['untracked'] += quant.quantity - quant.reserved_quantity
                else:
                    availaible_quantities[quant.lot_id] += quant.quantity - quant.reserved_quantity
            if allow_negative:
                return sum(availaible_quantities.values())
            else:
                return sum([available_quantity for available_quantity in availaible_quantities.values() if float_compare(available_quantity, 0, precision_rounding=rounding) > 0])

    def _get_reserve_quantity(self, product_id, location_id, quantity, uom_id=None, lot_id=None, package_id=None, owner_id=None, strict=False):
        """ Get the quantity available to reserve for the set of quants
        sharing the combination of `product_id, location_id` if `strict` is set to False or sharing
        the *exact same characteristics* otherwise. If no quants are in self, `_gather` will do a search to fetch the quants
        Typically, this method is called before the `stock.move.line` creation to know the reserved_qty that could be use.
        It's also called by `_update_reserve_quantity` to find the quant to reserve.

        :return: a list of tuples (quant, quantity_reserved) showing on which quant the reservation
            could be done and how much the system is able to reserve on it
        """
        self = self.sudo()
        rounding = product_id.uom_id.rounding

        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict, qty=quantity)

        # avoid quants with negative qty to not lower available_qty
        available_quantity = quants._get_available_quantity(product_id, location_id, lot_id, package_id, owner_id, strict)

        # do full packaging reservation when it's needed
        if self.env.context.get('packaging_uom_id') and product_id.product_tmpl_id.categ_id.packaging_reserve_method == "full":
            available_quantity = self.env.context.get('packaging_uom_id')._check_qty(available_quantity, product_id.uom_id, "DOWN")

        quantity = min(quantity, available_quantity)

        # `quantity` is in the quants unit of measure. There's a possibility that the move's
        # unit of measure won't be respected if we blindly reserve this quantity, a common usecase
        # is if the move's unit of measure's rounding does not allow fractional reservation. We chose
        # to convert `quantity` to the move's unit of measure with a down rounding method and
        # then get it back in the quants unit of measure with an half-up rounding_method. This
        # way, we'll never reserve more than allowed. We do not apply this logic if
        # `available_quantity` is brought by a chained move line. In this case, `_prepare_move_line_vals`
        # will take care of changing the UOM to the UOM of the product.
        if not strict and uom_id and product_id.uom_id != uom_id:
            quantity_move_uom = product_id.uom_id._compute_quantity(quantity, uom_id, rounding_method='DOWN')
            quantity = uom_id._compute_quantity(quantity_move_uom, product_id.uom_id, rounding_method='HALF-UP')

        if product_id.tracking == 'serial':
            if float_compare(quantity, int(quantity), precision_rounding=rounding) != 0:
                quantity = 0

        reserved_quants = []

        if float_compare(quantity, 0, precision_rounding=rounding) > 0:
            # if we want to reserve
            available_quantity = sum(quants.filtered(lambda q: float_compare(q.quantity, 0, precision_rounding=rounding) > 0).mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
        elif float_compare(quantity, 0, precision_rounding=rounding) < 0:
            # if we want to unreserve
            available_quantity = sum(quants.mapped('reserved_quantity'))
            if float_compare(abs(quantity), available_quantity, precision_rounding=rounding) > 0:
                raise UserError(_('It is not possible to unreserve more products of %s than you have in stock.', product_id.display_name))
        else:
            return reserved_quants

        negative_reserved_quantity = defaultdict(float)
        for quant in quants:
            if float_compare(quant.quantity - quant.reserved_quantity, 0, precision_rounding=rounding) < 0:
                negative_reserved_quantity[(quant.location_id, quant.lot_id, quant.package_id, quant.owner_id)] += quant.quantity - quant.reserved_quantity
        for quant in quants:
            if float_compare(quantity, 0, precision_rounding=rounding) > 0:
                max_quantity_on_quant = quant.quantity - quant.reserved_quantity
                if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
                    continue
                negative_quantity = negative_reserved_quantity[(quant.location_id, quant.lot_id, quant.package_id, quant.owner_id)]
                if negative_quantity:
                    negative_qty_to_remove = min(abs(negative_quantity), max_quantity_on_quant)
                    negative_reserved_quantity[(quant.location_id, quant.lot_id, quant.package_id, quant.owner_id)] += negative_qty_to_remove
                    max_quantity_on_quant -= negative_qty_to_remove
                if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
                    continue
                max_quantity_on_quant = min(max_quantity_on_quant, quantity)
                reserved_quants.append((quant, max_quantity_on_quant))
                quantity -= max_quantity_on_quant
                available_quantity -= max_quantity_on_quant
            else:
                max_quantity_on_quant = min(quant.reserved_quantity, abs(quantity))
                reserved_quants.append((quant, -max_quantity_on_quant))
                quantity += max_quantity_on_quant
                available_quantity += max_quantity_on_quant

            if float_is_zero(quantity, precision_rounding=rounding) or float_is_zero(available_quantity, precision_rounding=rounding):
                break
        return reserved_quants

    def _get_quants_by_products_locations(self, product_ids, location_ids, extra_domain=False):
        res = defaultdict(lambda: self.env['stock.quant'])
        if product_ids and location_ids:
            domain = [
                ('product_id', 'in', product_ids.ids),
                ('location_id', 'child_of', location_ids.ids)
            ]
            if extra_domain:
                domain = expression.AND([domain, extra_domain])
            needed_quants = self.env['stock.quant']._read_group(
                domain,
                ['product_id', 'location_id', 'lot_id', 'package_id', 'owner_id'],
                ['id:recordset'], order="lot_id"
            )
            for product, loc, lot, package, owner, quants in needed_quants:
                res[product.id, loc.id, lot.id, package.id, owner.id] = quants
        return res

    @api.onchange('location_id', 'product_id', 'lot_id', 'package_id', 'owner_id')
    def _onchange_location_or_product_id(self):
        vals = {}

        # Once the new line is complete, fetch the new theoretical values.
        if self.product_id and self.location_id:
            # Sanity check if a lot has been set.
            if self.lot_id:
                if self.tracking == 'none' or self.product_id != self.lot_id.product_id:
                    vals['lot_id'] = None

            quant = self._gather(
                self.product_id, self.location_id, lot_id=self.lot_id,
                package_id=self.package_id, owner_id=self.owner_id, strict=True)
            self.quantity = sum(quant.filtered(lambda q: q.lot_id == self.lot_id).mapped('quantity'))

            # Special case: directly set the quantity to one for serial numbers,
            # it'll trigger `inventory_quantity` compute.
            if self.lot_id and self.tracking == 'serial':
                vals['inventory_quantity'] = 1
                vals['inventory_quantity_auto_apply'] = 1

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

    @api.onchange('lot_id')
    def _onchange_serial_number(self):
        if self.lot_id and self.product_id.tracking == 'serial':
            message, dummy = self.env['stock.quant'].sudo()._check_serial_number(self.product_id,
                                                                                 self.lot_id,
                                                                                 self.company_id)
            if message:
                return {'warning': {'title': _('Warning'), 'message': message}}

    @api.onchange('product_id', 'company_id')
    def _onchange_product_id(self):
        if self.location_id:
            return
        if self.product_id.tracking in ['lot', 'serial']:
            previous_quants = self.env['stock.quant'].search([
                ('product_id', '=', self.product_id.id),
                ('location_id.usage', 'in', ['internal', 'transit'])], limit=1, order='create_date desc')
            if previous_quants:
                self.location_id = previous_quants.location_id
        if not self.location_id:
            company_id = self.company_id and self.company_id.id or self.env.company.id
            self.location_id = self.env['stock.warehouse'].search(
                [('company_id', '=', company_id)], limit=1
            ).lot_stock_id

    def _apply_inventory(self):
        # Consider the inventory_quantity as set => recompute the inventory_diff_quantity if needed
        self.inventory_quantity_set = True
        move_vals = []
        for quant in self:
            # Create and validate a move so that the quant matches its `inventory_quantity`.
            if float_compare(quant.inventory_diff_quantity, 0, precision_rounding=quant.product_uom_id.rounding) > 0:
                move_vals.append(
                    quant._get_inventory_move_values(quant.inventory_diff_quantity,
                                                     quant.product_id.with_company(quant.company_id).property_stock_inventory,
                                                     quant.location_id, package_dest_id=quant.package_id))
            else:
                move_vals.append(
                    quant._get_inventory_move_values(-quant.inventory_diff_quantity,
                                                     quant.location_id,
                                                     quant.product_id.with_company(quant.company_id).property_stock_inventory,
                                                     package_id=quant.package_id))
        moves = self.env['stock.move'].with_context(inventory_mode=False).create(move_vals)
        moves._action_done()
        self.location_id.sudo().write({'last_inventory_date': fields.Date.today()})
        date_by_location = {loc: loc._get_next_inventory_date() for loc in self.mapped('location_id')}
        for quant in self:
            quant.inventory_date = date_by_location[quant.location_id]
        self.action_clear_inventory_quantity()

    @api.model
    def _update_available_quantity(self, product_id, location_id, quantity=False, reserved_quantity=False, lot_id=None, package_id=None, owner_id=None, in_date=None):
        """ Increase or decrease `quantity` or 'reserved quantity' of a set of quants for a given set of
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
        if not (quantity or reserved_quantity):
            raise ValidationError(_('Quantity or Reserved Quantity should be set.'))
        self = self.sudo()
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True)
        if lot_id and quantity > 0:
            quants = quants.filtered(lambda q: q.lot_id)

        if location_id.should_bypass_reservation():
            incoming_dates = []
        else:
            incoming_dates = [quant.in_date for quant in quants if quant.in_date and
                              float_compare(quant.quantity, 0, precision_rounding=quant.product_uom_id.rounding) > 0]
        if in_date:
            incoming_dates += [in_date]
        # If multiple incoming dates are available for a given lot_id/package_id/owner_id, we
        # consider only the oldest one as being relevant.
        if incoming_dates:
            in_date = min(incoming_dates)
        else:
            in_date = fields.Datetime.now()

        quant = None
        if quants:
            # quants are already ordered in _gather
            # lock the first available
            quant = quants.try_lock_for_update(allow_referencing=True, limit=1)

        if quant:
            vals = {'in_date': in_date}
            if quantity:
                vals['quantity'] = quant.quantity + quantity
            if reserved_quantity:
                vals['reserved_quantity'] = max(0, quant.reserved_quantity + reserved_quantity)
            quant.write(vals)
        else:
            vals = {
                'product_id': product_id.id,
                'location_id': location_id.id,
                'lot_id': lot_id and lot_id.id,
                'package_id': package_id and package_id.id,
                'owner_id': owner_id and owner_id.id,
                'in_date': in_date,
            }
            if quantity:
                vals['quantity'] = quantity
            if reserved_quantity:
                vals['reserved_quantity'] = reserved_quantity
            self.create(vals)
        return self._get_available_quantity(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True, allow_negative=True), in_date

    @api.model
    def _update_reserved_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, strict=True):
        """ Increase or decrease `reserved_quantity` of a set of quants for a given set of
        product_id/location_id/lot_id/package_id/owner_id.

        :param product_id:
        :param location_id:
        :param quantity:
        :param lot_id:
        :param package_id:
        :param owner_id:
        :return: available_quantity
        """
        self._update_available_quantity(product_id, location_id, reserved_quantity=quantity, lot_id=lot_id, package_id=package_id, owner_id=owner_id)

    @api.model
    def _unlink_zero_quants(self):
        """ _update_available_quantity may leave quants with no
        quantity and no reserved_quantity. It used to directly unlink
        these zero quants but this proved to hurt the performance as
        this method is often called in batch and each unlink invalidate
        the cache. We defer the calls to unlink in this method.
        """
        precision_digits = max(6, self.sudo().env.ref('uom.decimal_product_uom').digits * 2)
        # Use a select instead of ORM search for UoM robustness.
        query = """SELECT id FROM stock_quant WHERE (round(quantity::numeric, %s) = 0 OR quantity IS NULL)
                                                     AND round(reserved_quantity::numeric, %s) = 0
                                                     AND (round(inventory_quantity::numeric, %s) = 0 OR inventory_quantity IS NULL)
                                                     AND user_id IS NULL;"""
        params = (precision_digits, precision_digits, precision_digits)
        self.env.cr.execute(query, params)
        quants = self.env['stock.quant'].browse([quant['id'] for quant in self.env.cr.dictfetchall()])
        quants.sudo().unlink()

    @api.model
    def _clean_reservations(self):
        reserved_quants = self.env['stock.quant']._read_group(
            [('reserved_quantity', '!=', 0)],
            ['product_id', 'location_id', 'lot_id', 'package_id', 'owner_id'],
            ['reserved_quantity:sum', 'id:recordset'],
        )
        reserved_move_lines = self.env['stock.move.line']._read_group(
            [
                ('state', 'in', ['assigned', 'partially_available', 'waiting', 'confirmed']),
                ('quantity_product_uom', '!=', 0),
                ('product_id.is_storable', '=', True),
            ],
            ['product_id', 'location_id', 'lot_id', 'package_id', 'owner_id'],
            ['quantity_product_uom:sum'],
        )
        reserved_move_lines = {
            (product, location, lot, package, owner): reserved_quantity
            for product, location, lot, package, owner, reserved_quantity in reserved_move_lines
        }
        for product, location, lot, package, owner, reserved_quantity, quants in reserved_quants:
            ml_reserved_qty = reserved_move_lines.get((product, location, lot, package, owner), 0)
            if location.should_bypass_reservation() or (product.tracking in ('lot', 'serial') and not lot):
                quants._update_reserved_quantity(product, location, -reserved_quantity, lot_id=lot, package_id=package, owner_id=owner)
            elif float_compare(reserved_quantity, ml_reserved_qty, precision_rounding=product.uom_id.rounding) != 0:
                quants._update_reserved_quantity(product, location, ml_reserved_qty - reserved_quantity, lot_id=lot, package_id=package, owner_id=owner)
            if ml_reserved_qty:
                del reserved_move_lines[(product, location, lot, package, owner)]

        for (product, location, lot, package, owner), reserved_quantity in reserved_move_lines.items():
            if location.should_bypass_reservation() or (product.tracking in ('lot', 'serial') and not lot):
                continue
            else:
                self.env['stock.quant']._update_reserved_quantity(product, location, reserved_quantity, lot_id=lot, package_id=package, owner_id=owner)

    @api.model
    def _merge_quants(self):
        """ In a situation where one transaction is updating a quant via
        `_update_available_quantity` and another concurrent one calls this function with the same
        argument, we’ll create a new quant in order for these transactions to not rollback. This
        method will find and deduplicate these quants.
        """
        params = []
        query = """WITH
                        dupes AS (
                            SELECT min(id) as to_update_quant_id,
                                (array_agg(id ORDER BY id))[2:array_length(array_agg(id), 1)] as to_delete_quant_ids,
                                GREATEST(0, SUM(reserved_quantity)) as reserved_quantity,
                                SUM(inventory_quantity) as inventory_quantity,
                                SUM(quantity) as quantity,
                                MIN(in_date) as in_date
                            FROM stock_quant
        """
        if self._ids:
            query += """
                            WHERE
                                location_id in %s
                                AND product_id in %s
            """
            params = [tuple(self.location_id.ids), tuple(self.product_id.ids)]
        query += """
                            GROUP BY product_id, company_id, location_id, lot_id, package_id, owner_id
                            HAVING count(id) > 1
                        ),
                        _up AS (
                            UPDATE stock_quant q
                                SET quantity = d.quantity,
                                    reserved_quantity = d.reserved_quantity,
                                    inventory_quantity = d.inventory_quantity,
                                    in_date = d.in_date
                            FROM dupes d
                            WHERE d.to_update_quant_id = q.id
                        )
                   DELETE FROM stock_quant WHERE id in (SELECT unnest(to_delete_quant_ids) from dupes)
        """
        try:
            with self.env.cr.savepoint():
                self.env.cr.execute(query, params)
                self.env.invalidate_all()
        except Error as e:
            _logger.info('an error occurred while merging quants: %s', e.pgerror)

    @api.model
    def _quant_tasks(self):
        self._merge_quants()
        self._clean_reservations()
        self._unlink_zero_quants()

    @api.model
    def _is_inventory_mode(self):
        """ Used to control whether a quant was written on or created during an
        "inventory session", meaning a mode where we need to create the stock.move
        record necessary to be consistent with the `inventory_quantity` field.
        """
        return self.env.context.get('inventory_mode') and self.env.user.has_group('stock.group_stock_user')

    @api.model
    def _get_inventory_fields_create(self):
        """ Returns a list of fields user can edit when he want to create a quant in `inventory_mode`.
        """
        return ['product_id', 'owner_id'] + self._get_inventory_fields_write()

    @api.model
    def _get_inventory_fields_write(self):
        """ Returns a list of fields user can edit when he want to edit a quant in `inventory_mode`.
        """
        fields = ['inventory_quantity', 'inventory_quantity_auto_apply', 'inventory_diff_quantity',
                  'inventory_date', 'user_id', 'inventory_quantity_set', 'is_outdated', 'lot_id',
                  'location_id', 'package_id']
        return fields

    def _get_inventory_move_values(self, qty, location_id, location_dest_id, package_id=False, package_dest_id=False):
        """ Called when user manually set a new quantity (via `inventory_quantity`)
        just before creating the corresponding stock move.

        :param location_id: `stock.location`
        :param location_dest_id: `stock.location`
        :param package_id: `stock.quant.package`
        :param package_dest_id: `stock.quant.package`
        :return: dict with all values needed to create a new `stock.move` with its move line.
        """
        self.ensure_one()
        if self.env.context.get('inventory_name'):
            name = self.env.context.get('inventory_name')
        elif fields.Float.is_zero(qty, precision_rounding=self.product_uom_id.rounding):
            name = _('Product Quantity Confirmed')
        else:
            name = _('Product Quantity Updated')
        if self.user_id and self.user_id.id != SUPERUSER_ID:
            name += f' ({self.user_id.display_name})'

        return {
            'name': name,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'product_uom_qty': qty,
            'company_id': self.company_id.id or self.env.company.id,
            'state': 'confirmed',
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
            'restrict_partner_id':  self.owner_id.id,
            'is_inventory': True,
            'picked': True,
            'move_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'product_uom_id': self.product_uom_id.id,
                'quantity': qty,
                'location_id': location_id.id,
                'location_dest_id': location_dest_id.id,
                'company_id': self.company_id.id or self.env.company.id,
                'lot_id': self.lot_id.id,
                'package_id': package_id.id if package_id else False,
                'result_package_id': package_dest_id.id if package_dest_id else False,
                'owner_id': self.owner_id.id,
            })]
        }

    def _set_view_context(self):
        """ Adds context when opening quants related views. """
        if not self.env.user.has_group('stock.group_stock_multi_locations'):
            company_user = self.env.company
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
            if warehouse:
                self = self.with_context(default_location_id=warehouse.lot_stock_id.id, hide_location=not self.env.context.get('always_show_loc', False))

        # If user have rights to write on quant, we set quants in inventory mode.
        if self.env.user.has_group('stock.group_stock_user'):
            self = self.with_context(inventory_mode=True)
        return self

    @api.model
    def _get_quants_action(self, extend=False):
        """ Returns an action to open (non-inventory adjustment) quant view.
        Depending of the context (user have right to be inventory mode or not),
        the list view will be editable or readonly.

        :param domain: List for the domain, empty by default.
        :param extend: If True, enables form, graph and pivot views. False by default.
        """
        if not self.env['ir.config_parameter'].sudo().get_param('stock.skip_quant_tasks'):
            self._quant_tasks()
        ctx = dict(self.env.context or {})
        ctx['inventory_report_mode'] = True
        ctx.pop('group_by', None)

        action = self.env['ir.actions.act_window']._for_xml_id('stock.stock_quant_action')

        form_view = self.env.ref('stock.view_stock_quant_form_editable').id
        if self.env.context.get('inventory_mode') and self.env.user.has_group('stock.group_stock_manager'):
            action['view_id'] = self.env.ref('stock.view_stock_quant_tree_editable').id
        else:
            action['view_id'] = self.env.ref('stock.view_stock_quant_tree').id
        action.update({
            'views': [
                (action['view_id'], 'list'),
                (form_view, 'form'),
            ],
            'context': ctx,
        })
        if extend:
            action.update({
                'view_mode': 'list,form,pivot,graph',
                'views': [
                    (action['view_id'], 'list'),
                    (form_view, 'form'),
                    (self.env.ref('stock.view_stock_quant_pivot').id, 'pivot'),
                    (self.env.ref('stock.stock_quant_view_graph').id, 'graph'),
                ],
            })
        # It's mainly define in the server action in order to call _get_quants_action when using the url
        action['path'] = "stock-locations"
        return action

    def _get_gs1_barcode(self, gs1_quantity_rules_ai_by_uom=False):
        """ Generates a GS1 barcode for the quant's properties (product, quantity and LN/SN.)

        :param gs1_quantity_rules_ai_by_uom: contains the products' GS1 AI paired with the UoM id
        :type gs1_quantity_rules_ai_by_uom: dict
        :return: str
        """
        self.ensure_one()
        gs1_quantity_rules_ai_by_uom = gs1_quantity_rules_ai_by_uom or {}
        barcode = ''

        # Product part.
        if self.product_id.valid_ean:
            barcode = self.product_id.barcode
            barcode = '01' + '0' * (14 - len(barcode)) + barcode
        elif self.tracking == 'none' or not self.lot_id:
            return ''  # Doesn't make sense to generate a GS1 barcode for qty with no other data.

        # Quantity part.
        if self.tracking != 'serial' or self.quantity > 1:
            quantity_ai = gs1_quantity_rules_ai_by_uom.get(self.product_uom_id.id)
            if quantity_ai:
                qty_str = str(int(self.quantity / self.product_uom_id.rounding))
                if len(qty_str) <= 6:
                    barcode += quantity_ai + '0' * (6 - len(qty_str)) + qty_str
            else:
                # No decimal indicator for GS1 Units, no better solution than rounding the qty.
                qty_str = str(int(round(self.quantity)))
                if len(qty_str) <= 8:
                    barcode += '30' + '0' * (8 - len(qty_str)) + qty_str

        # Tracking part (must be GS1 barcode's last part since we don't know SN/LN length.)
        if self.lot_id:
            if len(self.lot_id.name) > 20:
                # Cannot generate a valid GS1 barcode since the lot/serial number max length is
                # exceeded and this information is required if the LN/SN is present.
                return ''
            tracking_ai = '21' if self.tracking == 'serial' else '10'
            barcode += tracking_ai + self.lot_id.name
        return barcode

    def get_aggregate_barcodes(self):
        """ Generates and aggregates quants' barcodes. This method uses the config parameters
        `stock.agg_barcode_max_length` to determine the length limit of a single aggregate barcode
        (400 by default) and `stock.barcode_separator` to determine which character to use to
        separate individual encodings (this method can't work without this parameter and will return
        an empty list.) Depending on the number of quants, those parameters and the length of their
        barcode encodings, there can be one or more aggregate barcodes.

        :return: list
        """
        agg_barcode_max_length = int(self.env['ir.config_parameter'].sudo().get_param('stock.agg_barcode_max_length', 400))
        barcode_separator = self.env['ir.config_parameter'].sudo().get_param('stock.barcode_separator')
        if not barcode_separator:
            return []  # A barcode separator is mandatory to be able to aggregate barcodes.

        eol_char = '\t'  # Added at the end of aggregate barcodes to end `barcode_scanned` event.
        aggregate_barcodes = []
        aggregate_barcode = ""

        # Searches all GS1 rules linked to an UoM other than Unit and retrieves their AI.
        uom_unit_id = self.env.ref('uom.product_uom_unit').id
        gs1_quantity_rules = self.env['barcode.rule'].search([
            ('associated_uom_id', '!=', False),
            ('associated_uom_id', '!=', uom_unit_id),
            ('is_gs1_nomenclature', '=', True)]
        )
        gs1_quantity_rules_ai_by_uom = {}

        for rule in gs1_quantity_rules:
            decimal = str(len(f'{rule.associated_uom_id.rounding:.10f}'.rstrip('0').split('.')[1]))
            rule_ai = rule.pattern[1:4] + decimal
            gs1_quantity_rules_ai_by_uom[rule.associated_uom_id.id] = rule_ai

        previous_product = self.env['product.product']
        for quant in self:
            if not quant.product_id.barcode:
                continue
            barcode = ""
            # In case the quant product's barcode is not GS1 compliant, add it first,
            # so that the lots and qty barcodes that follow it will be used for this product.
            if previous_product != quant.product_id:
                previous_product = quant.product_id
                if not quant.product_id.valid_ean:
                    barcode += quant.product_id.barcode
            # Gets quant's barcode (either a GS1 barcode or only a serial number.)
            quant_gs1_barcode = quant._get_gs1_barcode(gs1_quantity_rules_ai_by_uom)
            if quant_gs1_barcode:
                barcode += (barcode_separator if barcode else '') + quant_gs1_barcode
            elif quant.tracking == 'serial':
                barcode += (barcode_separator if barcode else '') + quant.lot_id.name
            # If aggregate barcode will be too long, adds it to the result list and resets it.
            if aggregate_barcode and len(aggregate_barcode + barcode) > agg_barcode_max_length:
                aggregate_barcodes.append(aggregate_barcode + eol_char)
                aggregate_barcode = ""
            if barcode:
                if aggregate_barcode and aggregate_barcode[-1] != barcode_separator:
                    aggregate_barcode += barcode_separator
                aggregate_barcode += barcode

        if aggregate_barcode:
            aggregate_barcodes.append(aggregate_barcode + eol_char)

        return aggregate_barcodes

    @api.model
    def _check_serial_number(self, product_id, lot_id, company_id, source_location_id=None, ref_doc_location_id=None):
        """ Checks for duplicate serial numbers (SN) when assigning a SN (i.e. no source_location_id)
        and checks for potential incorrect location selection of a SN when using a SN (i.e.
        source_location_id). Returns warning message of all locations the SN is located at and
        (optionally) a recommended source location of the SN (when using SN from incorrect location).
        This function is designed to be used by onchange functions across differing situations including,
        but not limited to scrap, incoming picking SN encoding, and outgoing picking SN selection.

        :param product_id: `product.product` product to check SN for
        :param lot_id: `stock.production.lot` SN to check
        :param company_id: `res.company` company to check against (i.e. we ignore duplicate SNs across
            different companies for lots defined with a company)
        :param source_location_id: `stock.location` optional source location if using the SN rather
            than assigning it
        :param ref_doc_location_id: `stock.location` optional reference document location for
            determining recommended location. This is param expected to only be used when a
            `source_location_id` is provided.
        :return: tuple(message, recommended_location) If not None, message is a string expected to be
            used in warning message dict and recommended_location is a `location_id`
        """
        message = None
        recommended_location = None
        if product_id.tracking == 'serial':
            internal_domain = [('location_id.usage', 'in', ('internal', 'transit'))]
            if lot_id.company_id:
                internal_domain = expression.AND([internal_domain, [('company_id', '=', company_id.id)]])
            quants = self.env['stock.quant'].search([('product_id', '=', product_id.id),
                                                     ('lot_id', '=', lot_id.id),
                                                     ('quantity', '!=', 0),
                                                     '|', ('location_id.usage', '=', 'customer'),
                                                           *internal_domain])
            sn_locations = quants.mapped('location_id')
            if quants:
                if not source_location_id:
                    # trying to assign an already existing SN
                    message = _('The Serial Number (%(serial_number)s) is already used in location(s): %(location_list)s.\n\n'
                                'Is this expected? For example, this can occur if a delivery operation is validated '
                                'before its corresponding receipt operation is validated. In this case the issue will be solved '
                                'automatically once all steps are completed. Otherwise, the serial number should be corrected to '
                                'prevent inconsistent data.',
                                serial_number=lot_id.name, location_list=sn_locations.mapped('display_name'))

                elif source_location_id and source_location_id not in sn_locations:
                    # using an existing SN in the wrong location
                    recommended_location = self.env['stock.location']
                    if ref_doc_location_id:
                        for location in sn_locations:
                            if ref_doc_location_id.parent_path in location.parent_path:
                                recommended_location = location
                                break
                    else:
                        for location in sn_locations:
                            if location.usage != 'customer':
                                recommended_location = location
                                break
                    if recommended_location and recommended_location.company_id == company_id:
                        message = _('Serial number (%(serial_number)s) is not located in %(source_location)s, but is located in location(s): %(other_locations)s.\n\n'
                                    'Source location for this move will be changed to %(recommended_location)s',
                                    serial_number=lot_id.name,
                                    source_location=source_location_id.display_name,
                                    other_locations=sn_locations.mapped('display_name'),
                                    recommended_location=recommended_location.display_name)
                    else:
                        message = _('Serial number (%(serial_number)s) is not located in %(source_location)s, but is located in location(s): %(other_locations)s.\n\n'
                                    'Please correct this to prevent inconsistent data.',
                                    serial_number=lot_id.name,
                                    source_location=source_location_id.display_name,
                                    other_locations=sn_locations.mapped('display_name'))
                        recommended_location = None
        return message, recommended_location

    def move_quants(self, location_dest_id=False, package_dest_id=False, message=False, unpack=False):
        """ Directly move a stock.quant to another location and/or package by creating a stock.move.

        :param location_dest_id: `stock.location` destination location for the quants
        :param package_dest_id: `stock.quant.package´ destination package for the quants
        :param message: String to fill the reference field on the generated stock.move
        :param unpack: set to True when needing to unpack the quant
        """
        message = message or _('Quantity Relocated')
        move_vals = []
        for quant in self:
            result_package_id = package_dest_id  # temp variable to keep package_dest_id unchanged
            if not unpack and not package_dest_id:
                result_package_id = quant.package_id
            move_vals.append(quant.with_context(inventory_name=message)._get_inventory_move_values(
                quant.quantity,
                quant.location_id,
                location_dest_id or quant.location_id,
                quant.package_id,
                result_package_id))
        moves = self.env['stock.move'].create(move_vals)
        moves._action_done()


class StockQuantPackage(models.Model):
    """ Packages containing quants and/or other packages """
    _name = 'stock.quant.package'
    _description = "Packages"
    _order = 'name'

    name = fields.Char(
        'Package Reference', copy=False, index='trigram', required=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('stock.quant.package') or _('Unknown Pack'))
    quant_ids = fields.One2many('stock.quant', 'package_id', 'Bulk Content', readonly=True,
        domain=['|', ('quantity', '!=', 0), ('reserved_quantity', '!=', 0)])
    package_type_id = fields.Many2one(
        'stock.package.type', 'Package Type', index=True)
    location_id = fields.Many2one(
        'stock.location', 'Location', compute='_compute_package_info',
        index=True, readonly=False, store=True)
    company_id = fields.Many2one(
        'res.company', 'Company', compute='_compute_package_info',
        index=True, readonly=True, store=True)
    owner_id = fields.Many2one(
        'res.partner', 'Owner', compute='_compute_owner_id', search='_search_owner',
        readonly=True, compute_sudo=True)
    package_use = fields.Selection([
        ('disposable', 'Disposable Box'),
        ('reusable', 'Reusable Box'),
        ], string='Package Use', default='disposable', required=True,
        help="""Reusable boxes are used for batch picking and emptied afterwards to be reused. In the barcode application, scanning a reusable box will add the products in this box.
        Disposable boxes aren't reused, when scanning a disposable box in the barcode application, the contained products are added to the transfer.""")
    shipping_weight = fields.Float(string='Shipping Weight', help="Total weight of the package.")
    valid_sscc = fields.Boolean('Package name is valid SSCC', compute='_compute_valid_sscc')
    pack_date = fields.Date('Pack Date', default=fields.Date.today)

    @api.depends('name', 'package_type_id.packaging_length', 'package_type_id.width', 'package_type_id.height')
    @api.depends_context('formatted_display_name')
    def _compute_display_name(self):
        packages_to_process_ids = []
        for package in self:
            if package.env.context.get('formatted_display_name') and package.package_type_id and package.package_type_id.packaging_length and package.package_type_id.width and package.package_type_id.height:
                package.display_name = f"{package.name}\t--{package.package_type_id.packaging_length} x {package.package_type_id.width} x {package.package_type_id.height}--"
            else:
                packages_to_process_ids.append(package.id)
        if packages_to_process_ids:
            super(StockQuantPackage, self.env['stock.quant.package'].browse(packages_to_process_ids))._compute_display_name()

    @api.depends('quant_ids.location_id', 'quant_ids.company_id')
    def _compute_package_info(self):
        for package in self:
            package.location_id = False
            package.company_id = False
            quants = package.quant_ids.filtered(lambda q: float_compare(q.quantity, 0, precision_rounding=q.product_uom_id.rounding) > 0)
            if quants:
                package.location_id = quants[0].location_id
                if all(q.company_id == quants[0].company_id for q in package.quant_ids):
                    package.company_id = quants[0].company_id

    @api.depends('quant_ids.owner_id')
    def _compute_owner_id(self):
        for package in self:
            package.owner_id = False
            if package.quant_ids and all(
                q.owner_id == package.quant_ids[0].owner_id for q in package.quant_ids
            ):
                package.owner_id = package.quant_ids[0].owner_id

    @api.depends('name')
    def _compute_valid_sscc(self):
        self.valid_sscc = False
        for package in self:
            if package.name:
                package.valid_sscc = check_barcode_encoding(package.name, 'sscc')

    def _search_owner(self, operator, value):
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            return NotImplemented
        return [('quant_ids.owner_id', operator, value)]

    def write(self, vals):
        if 'location_id' in vals:
            if not vals['location_id']:
                raise UserError(_('Cannot remove the location of a non empty package'))
            if any(not pack.quant_ids for pack in self):
                raise UserError(_('Cannot move an empty package'))
            # create a move from the old location to new location
            location_dest_id = self.env['stock.location'].browse(vals['location_id'])
            quant_to_move = self.quant_ids.filtered(lambda q: q.quantity > 0)
            quant_to_move.move_quants(location_dest_id, message=_('Package manually relocated'))
        return super().write(vals)

    def unpack(self):
        self.quant_ids.move_quants(message=_("Quantities unpacked"), unpack=True)
        # Quant clean-up, mostly to avoid multiple quants of the same product. For example, unpack
        # 2 packages of 50, then reserve 100 => a quant of -50 is created at transfer validation.
        self.quant_ids._quant_tasks()

    def action_view_picking(self):
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
        domain = ['|', ('result_package_id', 'in', self.ids), ('package_id', 'in', self.ids)]
        pickings = self.env['stock.move.line'].search(domain).mapped('picking_id')
        action['domain'] = [('id', 'in', pickings.ids)]
        return action

    def _check_move_lines_map_quant(self, move_lines):
        """ This method checks that all product (quants) of self (package) are well present in the `move_line_ids`. """
        precision_digits = self.env['decimal.precision'].precision_get('Product Unit')

        def _keys_groupby(record):
            return record.product_id, record.lot_id

        grouped_quants = {}
        for k, g in groupby(self.quant_ids, key=_keys_groupby):
            grouped_quants[k] = sum(self.env['stock.quant'].concat(*g).mapped('quantity'))

        grouped_ops = {}
        for k, g in groupby(move_lines, key=_keys_groupby):
            grouped_ops[k] = sum(self.env['stock.move.line'].concat(*g).mapped('quantity'))

        if any(not float_is_zero(grouped_quants.get(key, 0) - grouped_ops.get(key, 0), precision_digits=precision_digits) for key in grouped_quants) \
                or any(not float_is_zero(grouped_ops.get(key, 0) - grouped_quants.get(key, 0), precision_digits=precision_digits) for key in grouped_ops):
            return False
        return True

    def _get_weight(self, picking_id=False):
        res = {}
        if picking_id:
            package_weights = defaultdict(float)
            res_groups = self.env['stock.move.line']._read_group(
                [('result_package_id', 'in', self.ids), ('product_id', '!=', False), ('picking_id', '=', picking_id)],
                ['result_package_id', 'product_id', 'product_uom_id', 'quantity'],
                ['__count'],
            )
            for result_package, product, product_uom, quantity, count in res_groups:
                package_weights[result_package.id] += (
                    count
                    * product_uom._compute_quantity(quantity, product.uom_id)
                    * product.weight
                )
        for package in self:
            weight = package.package_type_id.base_weight or 0.0
            if picking_id:
                res[package] = weight + package_weights[package.id]
            else:
                for quant in package.quant_ids:
                    weight += quant.quantity * quant.product_id.weight
                res[package] = weight
        return res
