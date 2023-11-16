# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import math
import time
from ast import literal_eval
from datetime import date, timedelta
from collections import defaultdict

from odoo import SUPERUSER_ID, _, api, Command, fields, models
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from odoo.addons.web.controllers.utils import clean_action
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, format_datetime, format_date, groupby
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class PickingType(models.Model):
    _name = "stock.picking.type"
    _description = "Picking Type"
    _order = 'sequence, id'
    _rec_names_search = ['name', 'warehouse_id.name']
    _check_company_auto = True

    name = fields.Char('Operation Type', required=True, translate=True)
    color = fields.Integer('Color')
    sequence = fields.Integer('Sequence', help="Used to order the 'All Operations' kanban view")
    sequence_id = fields.Many2one(
        'ir.sequence', 'Reference Sequence',
        check_company=True, copy=True)
    sequence_code = fields.Char('Sequence Prefix', required=True)
    default_location_src_id = fields.Many2one(
        'stock.location', 'Default Source Location', compute='_compute_default_location_src_id',
        check_company=True, store=True, readonly=False, precompute=True,
        help="This is the default source location when you create a picking manually with this operation type. It is possible however to change it or that the routes put another location. If it is empty, it will check for the supplier location on the partner. ")
    default_location_dest_id = fields.Many2one(
        'stock.location', 'Default Destination Location', compute='_compute_default_location_dest_id',
        check_company=True, store=True, readonly=False, precompute=True,
        help="This is the default destination location when you create a picking manually with this operation type. It is possible however to change it or that the routes put another location. If it is empty, it will check for the customer location on the partner. ")
    default_location_return_id = fields.Many2one('stock.location', 'Default returns location', check_company=True,
        help="This is the default location for returns created from a picking with this operation type.",
        domain="[('return_location', '=', 'True')]")
    code = fields.Selection([('incoming', 'Receipt'), ('outgoing', 'Delivery'), ('internal', 'Internal Transfer')], 'Type of Operation', required=True)
    return_picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type for Returns',
        check_company=True)
    show_entire_packs = fields.Boolean('Move Entire Packages', help="If ticked, you will be able to select entire packages to move")
    warehouse_id = fields.Many2one(
        'stock.warehouse', 'Warehouse', compute='_compute_warehouse_id', store=True, readonly=False, ondelete='cascade',
        check_company=True)
    active = fields.Boolean('Active', default=True)
    use_create_lots = fields.Boolean(
        'Create New Lots/Serial Numbers', default=True,
        compute='_compute_use_create_lots', store=True, readonly=False,
        help="If this is checked only, it will suppose you want to create new Lots/Serial Numbers, so you can provide them in a text field. ")
    use_existing_lots = fields.Boolean(
        'Use Existing Lots/Serial Numbers', default=True,
        compute='_compute_use_existing_lots', store=True, readonly=False,
        help="If this is checked, you will be able to choose the Lots/Serial Numbers. You can also decide to not put lots in this operation type.  This means it will create stock with no lot or not put a restriction on the lot taken. ")
    print_label = fields.Boolean(
        'Print Label',
        help="If this checkbox is ticked, label will be print in this operation.")
    # TODO: delete this field `show_operations`
    show_operations = fields.Boolean(
        'Show Detailed Operations', default=False,
        help="If this checkbox is ticked, the pickings lines will represent detailed stock operations. If not, the picking lines will represent an aggregate of detailed stock operations.")
    show_reserved = fields.Boolean(
        'Pre-fill Detailed Operations', default=True,
        compute='_compute_show_reserved', store=True,
        help="If this checkbox is ticked, Odoo will automatically pre-fill the detailed "
        "operations with the corresponding products, locations and lot/serial numbers. "
        "For moves that are returns, the detailed operations will always be prefilled, regardless of this option.")
    reservation_method = fields.Selection(
        [('at_confirm', 'At Confirmation'), ('manual', 'Manually'), ('by_date', 'Before scheduled date')],
        'Reservation Method', required=True, default='at_confirm',
        help="How products in transfers of this operation type should be reserved.")
    reservation_days_before = fields.Integer('Days', help="Maximum number of days before scheduled date that products should be reserved.")
    reservation_days_before_priority = fields.Integer('Days when starred', help="Maximum number of days before scheduled date that priority picking products should be reserved.")
    auto_show_reception_report = fields.Boolean(
        "Show Reception Report at Validation",
        help="If this checkbox is ticked, Odoo will automatically show the reception report (if there are moves to allocate to) when validating.")
    auto_print_delivery_slip = fields.Boolean(
        "Auto Print Delivery Slip",
        help="If this checkbox is ticked, Odoo will automatically print the delivery slip of a picking when it is validated.")
    auto_print_return_slip = fields.Boolean(
        "Auto Print Return Slip",
        help="If this checkbox is ticked, Odoo will automatically print the return slip of a picking when it is validated.")

    auto_print_product_labels = fields.Boolean(
        "Auto Print Product Labels",
        help="If this checkbox is ticked, Odoo will automatically print the product labels of a picking when it is validated.")
    product_label_format = fields.Selection([
        ('dymo', 'Dymo'),
        ('2x7xprice', '2 x 7 with price'),
        ('4x7xprice', '4 x 7 with price'),
        ('4x12', '4 x 12'),
        ('4x12xprice', '4 x 12 with price'),
        ('zpl', 'ZPL Labels'),
        ('zplxprice', 'ZPL Labels with price')], string="Product Label Format to auto-print", default='2x7xprice')
    auto_print_lot_labels = fields.Boolean(
        "Auto Print Lot/SN Labels",
        help="If this checkbox is ticked, Odoo will automatically print the lot/SN labels of a picking when it is validated.")
    lot_label_format = fields.Selection([
        ('4x12_lots', '4 x 12 - One per lot/SN'),
        ('4x12_units', '4 x 12 - One per unit'),
        ('zpl_lots', 'ZPL Labels - One per lot/SN'),
        ('zpl_units', 'ZPL Labels - One per unit')],
        string="Lot Label Format to auto-print", default='4x12_lots')
    auto_print_reception_report = fields.Boolean(
        "Auto Print Reception Report",
        help="If this checkbox is ticked, Odoo will automatically print the reception report of a picking when it is validated and has assigned moves.")
    auto_print_reception_report_labels = fields.Boolean(
        "Auto Print Reception Report Labels",
        help="If this checkbox is ticked, Odoo will automatically print the reception report labels of a picking when it is validated.")
    auto_print_packages = fields.Boolean(
        "Auto Print Packages",
        help="If this checkbox is ticked, Odoo will automatically print the packages and their contents of a picking when it is validated.")

    auto_print_package_label = fields.Boolean(
        "Auto Print Package Label",
        help="If this checkbox is ticked, Odoo will automatically print the package label when \"Put in Pack\" button is used.")
    package_label_to_print = fields.Selection(
        [('pdf', 'PDF'), ('zpl', 'ZPL')],
        "Package Label to Print", default='pdf')

    count_picking_draft = fields.Integer(compute='_compute_picking_count')
    count_picking_ready = fields.Integer(compute='_compute_picking_count')
    count_picking = fields.Integer(compute='_compute_picking_count')
    count_picking_waiting = fields.Integer(compute='_compute_picking_count')
    count_picking_late = fields.Integer(compute='_compute_picking_count')
    count_picking_backorders = fields.Integer(compute='_compute_picking_count')
    hide_reservation_method = fields.Boolean(compute='_compute_hide_reservation_method')
    barcode = fields.Char('Barcode', copy=False)
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda s: s.env.company.id, index=True)
    create_backorder = fields.Selection(
        [('ask', 'Ask'), ('always', 'Always'), ('never', 'Never')],
        'Create Backorder', required=True, default='ask',
        help="When validating a transfer:\n"
             " * Ask: users are asked to choose if they want to make a backorder for remaining products\n"
             " * Always: a backorder is automatically created for the remaining products\n"
             " * Never: remaining products are cancelled")
    show_picking_type = fields.Boolean(compute='_compute_show_picking_type')

    picking_properties_definition = fields.PropertiesDefinition("Picking Properties")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('sequence_id') and vals.get('sequence_code'):
                if vals.get('warehouse_id'):
                    wh = self.env['stock.warehouse'].browse(vals['warehouse_id'])
                    vals['sequence_id'] = self.env['ir.sequence'].sudo().create({
                        'name': wh.name + ' ' + _('Sequence') + ' ' + vals['sequence_code'],
                        'prefix': wh.code + '/' + vals['sequence_code'] + '/', 'padding': 5,
                        'company_id': wh.company_id.id,
                    }).id
                else:
                    vals['sequence_id'] = self.env['ir.sequence'].sudo().create({
                        'name': _('Sequence') + ' ' + vals['sequence_code'],
                        'prefix': vals['sequence_code'], 'padding': 5,
                        'company_id': vals.get('company_id') or self.env.company.id,
                    }).id
        return super().create(vals_list)

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        if 'name' not in default:
            default['name'] = _("%s (copy)", self.name)
        return super().copy(default=default)

    def write(self, vals):
        if 'company_id' in vals:
            for picking_type in self:
                if picking_type.company_id.id != vals['company_id']:
                    raise UserError(_("Changing the company of this record is forbidden at this point, you should rather archive it and create a new one."))
        if 'sequence_code' in vals:
            for picking_type in self:
                if picking_type.warehouse_id:
                    picking_type.sequence_id.sudo().write({
                        'name': picking_type.warehouse_id.name + ' ' + _('Sequence') + ' ' + vals['sequence_code'],
                        'prefix': picking_type.warehouse_id.code + '/' + vals['sequence_code'] + '/', 'padding': 5,
                        'company_id': picking_type.warehouse_id.company_id.id,
                    })
                else:
                    picking_type.sequence_id.sudo().write({
                        'name': _('Sequence') + ' ' + vals['sequence_code'],
                        'prefix': vals['sequence_code'], 'padding': 5,
                        'company_id': picking_type.env.company.id,
                    })
        return super(PickingType, self).write(vals)

    @api.depends('code')
    def _compute_hide_reservation_method(self):
        for rec in self:
            rec.hide_reservation_method = rec.code == 'incoming'

    def _compute_picking_count(self):
        domains = {
            'count_picking_draft': [('state', '=', 'draft')],
            'count_picking_waiting': [('state', 'in', ('confirmed', 'waiting'))],
            'count_picking_ready': [('state', '=', 'assigned')],
            'count_picking': [('state', 'in', ('assigned', 'waiting', 'confirmed'))],
            'count_picking_late': [('scheduled_date', '<', time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)), ('state', 'in', ('assigned', 'waiting', 'confirmed'))],
            'count_picking_backorders': [('backorder_id', '!=', False), ('state', 'in', ('confirmed', 'assigned', 'waiting'))],
        }
        for field_name, domain in domains.items():
            data = self.env['stock.picking']._read_group(domain +
                [('state', 'not in', ('done', 'cancel')), ('picking_type_id', 'in', self.ids)],
                ['picking_type_id'], ['__count'])
            count = {picking_type.id: count for picking_type, count in data}
            for record in self:
                record[field_name] = count.get(record.id, 0)

    @api.depends('warehouse_id')
    def _compute_display_name(self):
        """ Display 'Warehouse_name: PickingType_name' """
        for picking_type in self:
            if picking_type.warehouse_id:
                picking_type.display_name = f"{picking_type.warehouse_id.name}: {picking_type.name}"
            else:
                picking_type.display_name = picking_type.name

    @api.depends('code')
    def _compute_use_create_lots(self):
        for picking_type in self:
            if picking_type.code == 'incoming':
                picking_type.use_create_lots = True

    @api.depends('code')
    def _compute_use_existing_lots(self):
        for picking_type in self:
            if picking_type.code == 'outgoing':
                picking_type.use_existing_lots = True

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        # Try to reverse the `display_name` structure
        parts = name.split(': ')
        if len(parts) == 2:
            name_domain = [('warehouse_id.name', operator, parts[0]), ('name', operator, parts[1])]
            return self._search(expression.AND([name_domain, domain]), limit=limit, order=order)
        return super()._name_search(name, domain, operator, limit, order)

    @api.depends('code')
    def _compute_default_location_src_id(self):
        for picking_type in self:
            stock_location = picking_type.warehouse_id.lot_stock_id
            if picking_type.code == 'incoming':
                picking_type.default_location_src_id = self.env.ref('stock.stock_location_suppliers').id
            elif picking_type.code == 'outgoing':
                picking_type.default_location_src_id = stock_location.id

    @api.depends('code')
    def _compute_default_location_dest_id(self):
        for picking_type in self:
            stock_location = picking_type.warehouse_id.lot_stock_id
            if picking_type.code == 'incoming':
                picking_type.default_location_dest_id = stock_location.id
            elif picking_type.code == 'outgoing':
                picking_type.default_location_dest_id = self.env.ref('stock.stock_location_customers').id

    @api.depends('code')
    def _compute_print_label(self):
        for picking_type in self:
            if picking_type.code in ('incoming', 'internal'):
                picking_type.print_label = False
            elif picking_type.code == 'outgoing':
                picking_type.print_label = True

    @api.onchange('code')
    def _onchange_picking_code(self):
        if self.code == 'internal' and not self.user_has_groups('stock.group_stock_multi_locations'):
            return {
                'warning': {
                    'message': _('You need to activate storage locations to be able to do internal operation types.')
                }
            }

    @api.depends('company_id')
    def _compute_warehouse_id(self):
        for picking_type in self:
            if picking_type.warehouse_id:
                continue
            if picking_type.company_id:
                warehouse = self.env['stock.warehouse'].search([('company_id', '=', picking_type.company_id.id)], limit=1)
                picking_type.warehouse_id = warehouse
            else:
                picking_type.warehouse_id = False

    @api.depends('code')
    def _compute_show_reserved(self):
        for picking_type in self:
            if picking_type.code != 'incoming':
                picking_type.show_reserved = True

    @api.constrains('default_location_dest_id')
    def _check_default_location(self):
        for record in self:
            if record.code == 'mrp_operation' and record.default_location_dest_id.scrap_location:
                raise ValidationError(_("You cannot set a scrap location as the destination location for a manufacturing type operation."))

    def _get_action(self, action_xmlid):
        action = self.env["ir.actions.actions"]._for_xml_id(action_xmlid)
        if self:
            action['display_name'] = self.display_name

        context = {
            'search_default_picking_type_id': [self.id],
            'default_picking_type_id': self.id,
            'default_company_id': self.company_id.id,
        }

        action_context = literal_eval(action['context'])
        context = {**action_context, **context}
        action['context'] = context
        return action

    def get_action_picking_tree_late(self):
        return self._get_action('stock.action_picking_tree_late')

    def get_action_picking_tree_backorder(self):
        return self._get_action('stock.action_picking_tree_backorder')

    def get_action_picking_tree_waiting(self):
        return self._get_action('stock.action_picking_tree_waiting')

    def get_action_picking_tree_ready(self):
        return self._get_action('stock.action_picking_tree_ready')

    def get_action_picking_type_operations(self):
        return self._get_action('stock.action_get_picking_type_operations')

    def get_stock_picking_action_picking_type(self):
        return self._get_action('stock.stock_picking_action_picking_type')

    @api.depends('code')
    def _compute_show_picking_type(self):
        for record in self:
            record.show_picking_type = record.code in ['incoming', 'outgoing', 'internal']

    @api.constrains('sequence_id')
    def _check_sequence_code(self):
        domain = expression.OR([[('company_id', '=', record.company_id.id), ('name', '=', record.sequence_id.name)]
                                for record in self])
        duplicate_records = self.env['ir.sequence']._read_group(
            domain, ['company_id', 'name'], having=[('__count', '>', 1)])
        if duplicate_records:
            duplicate_names = [name for __, name in duplicate_records]
            raise UserError(_("Sequences %s already exist.",
                            ', '.join(duplicate_names)))

class Picking(models.Model):
    _name = "stock.picking"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Transfer"
    _order = "priority desc, scheduled_date asc, id desc"

    def _default_picking_type_id(self):
        picking_type_code = self.env.context.get('restricted_picking_type_code')
        if picking_type_code:
            picking_types = self.env['stock.picking.type'].search([
                ('code', '=', picking_type_code),
                ('company_id', '=', self.env.company.id),
            ])
            return picking_types[:1].id

    name = fields.Char(
        'Reference', default='/',
        copy=False, index='trigram', readonly=True)
    origin = fields.Char(
        'Source Document', index='trigram',
        help="Reference of the document")
    note = fields.Html('Notes')
    backorder_id = fields.Many2one(
        'stock.picking', 'Back Order of',
        copy=False, index='btree_not_null', readonly=True,
        check_company=True,
        help="If this shipment was split, then this field links to the shipment which contains the already processed part.")
    backorder_ids = fields.One2many('stock.picking', 'backorder_id', 'Back Orders')
    return_id = fields.Many2one('stock.picking', 'Return of', copy=False, index='btree_not_null', readonly=True, check_company=True,
        help="If this picking was created as a return of another picking, this field links to the original picking.")
    return_ids = fields.One2many('stock.picking', 'return_id', 'Returns')
    return_count = fields.Integer('# Returns', compute='_compute_return_count', compute_sudo=False)

    move_type = fields.Selection([
        ('direct', 'As soon as possible'), ('one', 'When all products are ready')], 'Shipping Policy',
        default='direct', required=True,
        help="It specifies goods to be deliver partially or all at once")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, tracking=True,
        help=" * Draft: The transfer is not confirmed yet. Reservation doesn't apply.\n"
             " * Waiting another operation: This transfer is waiting for another operation before being ready.\n"
             " * Waiting: The transfer is waiting for the availability of some products.\n(a) The shipping policy is \"As soon as possible\": no product could be reserved.\n(b) The shipping policy is \"When all products are ready\": not all the products could be reserved.\n"
             " * Ready: The transfer is ready to be processed.\n(a) The shipping policy is \"As soon as possible\": at least one product has been reserved.\n(b) The shipping policy is \"When all products are ready\": all product have been reserved.\n"
             " * Done: The transfer has been processed.\n"
             " * Cancelled: The transfer has been cancelled.")
    group_id = fields.Many2one(
        'procurement.group', 'Procurement Group',
        readonly=True, related='move_ids.group_id', store=True)
    priority = fields.Selection(
        PROCUREMENT_PRIORITIES, string='Priority', default='0',
        help="Products will be reserved first for the transfers with the highest priorities.")
    scheduled_date = fields.Datetime(
        'Scheduled Date', compute='_compute_scheduled_date', inverse='_set_scheduled_date', store=True,
        index=True, default=fields.Datetime.now, tracking=True,
        help="Scheduled time for the first part of the shipment to be processed. Setting manually a value here would set it as expected date for all the stock moves.")
    date_deadline = fields.Datetime(
        "Deadline", compute='_compute_date_deadline', store=True,
        help="Date Promise to the customer on the top level document (SO/PO)")
    has_deadline_issue = fields.Boolean(
        "Is late", compute='_compute_has_deadline_issue', store=True, default=False,
        help="Is late or will be late depending on the deadline and scheduled date")
    date = fields.Datetime(
        'Creation Date',
        default=fields.Datetime.now, tracking=True,
        help="Creation Date, usually the time of the order")
    date_done = fields.Datetime('Date of Transfer', copy=False, readonly=True, help="Date at which the transfer has been processed or cancelled.")
    delay_alert_date = fields.Datetime('Delay Alert Date', compute='_compute_delay_alert_date', search='_search_delay_alert_date')
    json_popover = fields.Char('JSON data for the popover widget', compute='_compute_json_popover')
    location_id = fields.Many2one(
        'stock.location', "Source Location",
        compute="_compute_location_id", store=True, precompute=True, readonly=False,
        check_company=True, required=True)
    location_dest_id = fields.Many2one(
        'stock.location', "Destination Location",
        compute="_compute_location_id", store=True, precompute=True, readonly=False,
        check_company=True, required=True)
    move_ids = fields.One2many('stock.move', 'picking_id', string="Stock Moves", copy=True)
    move_ids_without_package = fields.One2many(
        'stock.move', 'picking_id', string="Stock move", domain=['|', ('package_level_id', '=', False), ('picking_type_entire_packs', '=', False)])
    has_scrap_move = fields.Boolean(
        'Has Scrap Moves', compute='_has_scrap_move')
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type',
        required=True, readonly=True, index=True,
        default=_default_picking_type_id)
    picking_type_code = fields.Selection(
        related='picking_type_id.code',
        readonly=True)
    picking_type_entire_packs = fields.Boolean(related='picking_type_id.show_entire_packs')
    use_create_lots = fields.Boolean(related='picking_type_id.use_create_lots')
    use_existing_lots = fields.Boolean(related='picking_type_id.use_existing_lots')
    hide_picking_type = fields.Boolean(compute='_compute_hide_picking_type')
    partner_id = fields.Many2one(
        'res.partner', 'Contact',
        check_company=True)
    company_id = fields.Many2one(
        'res.company', string='Company', related='picking_type_id.company_id',
        readonly=True, store=True, index=True)
    user_id = fields.Many2one(
        'res.users', 'Responsible', tracking=True,
        domain=lambda self: [('groups_id', 'in', self.env.ref('stock.group_stock_user').id)],
        default=lambda self: self.env.user)
    move_line_ids = fields.One2many('stock.move.line', 'picking_id', 'Operations')
    move_line_ids_without_package = fields.One2many('stock.move.line', 'picking_id', 'Operations without package', domain=['|',('package_level_id', '=', False), ('picking_type_entire_packs', '=', False)])
    move_line_exist = fields.Boolean(
        'Has Pack Operations', compute='_compute_move_line_exist',
        help='Check the existence of pack operation on the picking')
    has_packages = fields.Boolean(
        'Has Packages', compute='_compute_has_packages',
        help='Check the existence of destination packages on move lines')
    show_check_availability = fields.Boolean(
        compute='_compute_show_check_availability',
        help='Technical field used to compute whether the button "Check Availability" should be displayed.')
    show_allocation = fields.Boolean(
        compute='_compute_show_allocation',
        help='Technical Field used to decide whether the button "Allocation" should be displayed.')
    owner_id = fields.Many2one(
        'res.partner', 'Assign Owner',
        check_company=True,
        help="When validating the transfer, the products will be assigned to this owner.")
    printed = fields.Boolean('Printed', copy=False)
    signature = fields.Image('Signature', help='Signature', copy=False, attachment=True)
    is_signed = fields.Boolean('Is Signed', compute="_compute_is_signed")
    is_locked = fields.Boolean(default=True, help='When the picking is not done this allows changing the '
                               'initial demand. When the picking is done this allows '
                               'changing the done quantities.')
    # Used to search on pickings
    product_id = fields.Many2one('product.product', 'Product', related='move_ids.product_id', readonly=True)
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial Number', related='move_line_ids.lot_id', readonly=True)
    # TODO: delete this field `show_operations`
    show_operations = fields.Boolean(related='picking_type_id.show_operations')
    show_reserved = fields.Boolean(related='picking_type_id.show_reserved')
    show_lots_text = fields.Boolean(compute='_compute_show_lots_text')
    has_tracking = fields.Boolean(compute='_compute_has_tracking')
    package_level_ids = fields.One2many('stock.package_level', 'picking_id')
    package_level_ids_details = fields.One2many('stock.package_level', 'picking_id')
    products_availability = fields.Char(
        string="Product Availability", compute='_compute_products_availability',
        help="Latest product availability status of the picking")
    products_availability_state = fields.Selection([
        ('available', 'Available'),
        ('expected', 'Expected'),
        ('late', 'Late')], compute='_compute_products_availability')
    # To remove in Master
    show_set_qty_button = fields.Boolean(compute='_compute_show_qty_button')
    show_clear_qty_button = fields.Boolean(compute='_compute_show_qty_button')

    picking_properties = fields.Properties(
        'Properties',
        definition='picking_type_id.picking_properties_definition',
        copy=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Reference must be unique per company!'),
    ]

    @api.depends()
    def _compute_show_qty_button(self):
        self.show_set_qty_button = False
        self.show_clear_qty_button = False

    def _compute_has_tracking(self):
        for picking in self:
            picking.has_tracking = any(m.has_tracking != 'none' for m in picking.move_ids)

    @api.depends('date_deadline', 'scheduled_date')
    def _compute_has_deadline_issue(self):
        for picking in self:
            picking.has_deadline_issue = picking.date_deadline and picking.date_deadline < picking.scheduled_date or False

    @api.depends('state')
    def _compute_hide_picking_type(self):
        for picking in self:
            picking.hide_picking_type = picking.state != "draft" and picking.ids and 'default_picking_type_id' in picking.env.context

    @api.depends('move_ids.delay_alert_date')
    def _compute_delay_alert_date(self):
        delay_alert_date_data = self.env['stock.move']._read_group([('id', 'in', self.move_ids.ids), ('delay_alert_date', '!=', False)], ['picking_id'], ['delay_alert_date:max'])
        delay_alert_date_data = {picking.id: delay_alert_date for picking, delay_alert_date in delay_alert_date_data}
        for picking in self:
            picking.delay_alert_date = delay_alert_date_data.get(picking.id, False)

    @api.depends('signature')
    def _compute_is_signed(self):
        for picking in self:
            picking.is_signed = picking.signature

    @api.depends('state', 'picking_type_code', 'scheduled_date', 'move_ids', 'move_ids.forecast_availability', 'move_ids.forecast_expected_date')
    def _compute_products_availability(self):
        pickings = self.filtered(lambda picking: picking.state in ('waiting', 'confirmed', 'assigned') and picking.picking_type_code == 'outgoing')
        pickings.products_availability_state = 'available'
        pickings.products_availability = _('Available')
        other_pickings = self - pickings
        other_pickings.products_availability = False
        other_pickings.products_availability_state = False

        all_moves = pickings.move_ids
        # Force to prefetch more than 1000 by 1000
        all_moves._fields['forecast_availability'].compute_value(all_moves)
        for picking in pickings:
            # In case of draft the behavior of forecast_availability is different : if forecast_availability < 0 then there is a issue else not.
            if any(float_compare(move.forecast_availability, 0 if move.state == 'draft' else move.product_qty, precision_rounding=move.product_id.uom_id.rounding) == -1 for move in picking.move_ids):
                picking.products_availability = _('Not Available')
                picking.products_availability_state = 'late'
            else:
                forecast_date = max(picking.move_ids.filtered('forecast_expected_date').mapped('forecast_expected_date'), default=False)
                if forecast_date:
                    picking.products_availability = _('Exp %s', format_date(self.env, forecast_date))
                    picking.products_availability_state = 'late' if picking.scheduled_date and picking.scheduled_date < forecast_date else 'expected'

    @api.depends('move_line_ids', 'picking_type_id.use_create_lots', 'picking_type_id.use_existing_lots', 'state')
    def _compute_show_lots_text(self):
        group_production_lot_enabled = self.user_has_groups('stock.group_production_lot')
        for picking in self:
            if not picking.move_line_ids and not picking.picking_type_id.use_create_lots:
                picking.show_lots_text = False
            elif group_production_lot_enabled and picking.picking_type_id.use_create_lots \
                    and not picking.picking_type_id.use_existing_lots and picking.state != 'done':
                picking.show_lots_text = True
            else:
                picking.show_lots_text = False

    def _compute_json_popover(self):
        picking_no_alert = self.filtered(lambda p: p.state in ('done', 'cancel') or not p.delay_alert_date)
        picking_no_alert.json_popover = False
        for picking in (self - picking_no_alert):
            picking.json_popover = json.dumps({
                'popoverTemplate': 'stock.PopoverStockRescheduling',
                'delay_alert_date': format_datetime(self.env, picking.delay_alert_date, dt_format=False),
                'late_elements': [{
                    'id': late_move.id,
                    'name': late_move.display_name,
                    'model': late_move._name,
                } for late_move in picking.move_ids.filtered(lambda m: m.delay_alert_date).move_orig_ids._delay_alert_get_documents()
                ]
            })

    @api.depends('move_type', 'move_ids.state', 'move_ids.picking_id')
    def _compute_state(self):
        ''' State of a picking depends on the state of its related stock.move
        - Draft: only used for "planned pickings"
        - Waiting: if the picking is not ready to be sent so if
          - (a) no quantity could be reserved at all or if
          - (b) some quantities could be reserved and the shipping policy is "deliver all at once"
        - Waiting another move: if the picking is waiting for another move
        - Ready: if the picking is ready to be sent so if:
          - (a) all quantities are reserved or if
          - (b) some quantities could be reserved and the shipping policy is "as soon as possible"
          - (c) it's an incoming picking
        - Done: if the picking is done.
        - Cancelled: if the picking is cancelled
        '''
        picking_moves_state_map = defaultdict(dict)
        picking_move_lines = defaultdict(set)
        for move in self.env['stock.move'].search([('picking_id', 'in', self.ids)]):
            picking_id = move.picking_id
            move_state = move.state
            picking_moves_state_map[picking_id.id].update({
                'any_draft': picking_moves_state_map[picking_id.id].get('any_draft', False) or move_state == 'draft',
                'all_cancel': picking_moves_state_map[picking_id.id].get('all_cancel', True) and move_state == 'cancel',
                'all_cancel_done': picking_moves_state_map[picking_id.id].get('all_cancel_done', True) and move_state in ('cancel', 'done'),
                'all_done_are_scrapped': picking_moves_state_map[picking_id.id].get('all_done_are_scrapped', True) and (move.scrapped if move_state == 'done' else True),
                'any_cancel_and_not_scrapped': picking_moves_state_map[picking_id.id].get('any_cancel_and_not_scrapped', False) or (move_state == 'cancel' and not move.scrapped),
            })
            picking_move_lines[picking_id.id].add(move.id)
        for picking in self:
            picking_id = (picking.ids and picking.ids[0]) or picking.id
            if not picking_moves_state_map[picking_id] or picking_moves_state_map[picking_id]['any_draft']:
                picking.state = 'draft'
            elif picking_moves_state_map[picking_id]['all_cancel']:
                picking.state = 'cancel'
            elif picking_moves_state_map[picking_id]['all_cancel_done']:
                if picking_moves_state_map[picking_id]['all_done_are_scrapped'] and picking_moves_state_map[picking_id]['any_cancel_and_not_scrapped']:
                    picking.state = 'cancel'
                else:
                    picking.state = 'done'
            else:
                if picking.location_id.should_bypass_reservation() and all(m.procure_method == 'make_to_stock' for m in picking.move_ids):
                    picking.state = 'assigned'
                else:
                    relevant_move_state = self.env['stock.move'].browse(picking_move_lines[picking_id])._get_relevant_state_among_moves()
                    if relevant_move_state == 'partially_available':
                        picking.state = 'assigned'
                    else:
                        picking.state = relevant_move_state

    @api.depends('move_ids.state', 'move_ids.date', 'move_type')
    def _compute_scheduled_date(self):
        for picking in self:
            moves_dates = picking.move_ids.filtered(lambda move: move.state not in ('done', 'cancel')).mapped('date')
            if picking.move_type == 'direct':
                picking.scheduled_date = min(moves_dates, default=picking.scheduled_date or fields.Datetime.now())
            else:
                picking.scheduled_date = max(moves_dates, default=picking.scheduled_date or fields.Datetime.now())

    @api.depends('move_ids.date_deadline', 'move_type')
    def _compute_date_deadline(self):
        for picking in self:
            if picking.move_type == 'direct':
                picking.date_deadline = min(picking.move_ids.filtered('date_deadline').mapped('date_deadline'), default=False)
            else:
                picking.date_deadline = max(picking.move_ids.filtered('date_deadline').mapped('date_deadline'), default=False)

    def _set_scheduled_date(self):
        for picking in self:
            if picking.state in ('done', 'cancel'):
                raise UserError(_("You cannot change the Scheduled Date on a done or cancelled transfer."))
            picking.move_ids.write({'date': picking.scheduled_date})

    def _has_scrap_move(self):
        for picking in self:
            # TDE FIXME: better implementation
            picking.has_scrap_move = bool(self.env['stock.move'].search_count([('picking_id', '=', picking.id), ('scrapped', '=', True)]))

    def _compute_move_line_exist(self):
        for picking in self:
            picking.move_line_exist = bool(picking.move_line_ids)

    def _compute_has_packages(self):
        domain = [('picking_id', 'in', self.ids), ('result_package_id', '!=', False)]
        cnt_by_picking = self.env['stock.move.line']._read_group(domain, ['picking_id'], ['__count'])
        cnt_by_picking = {picking.id: count for picking, count in cnt_by_picking}
        for picking in self:
            picking.has_packages = bool(cnt_by_picking.get(picking.id, False))

    @api.depends('state', 'move_ids.product_uom_qty', 'picking_type_code')
    def _compute_show_check_availability(self):
        """ According to `picking.show_check_availability`, the "check availability" button will be
        displayed in the form view of a picking.
        """
        for picking in self:
            if picking.state not in ('confirmed', 'waiting', 'assigned'):
                picking.show_check_availability = False
                continue
            if all(m.picked for m in picking.move_ids):
                picking.show_check_availability = False
                continue
            picking.show_check_availability = any(
                move.state in ('waiting', 'confirmed', 'partially_available') and
                float_compare(move.product_uom_qty, 0, precision_rounding=move.product_uom.rounding)
                for move in picking.move_ids
            )

    @api.depends('state', 'move_ids', 'picking_type_id')
    def _compute_show_allocation(self):
        self.show_allocation = False
        if not self.user_has_groups('stock.group_reception_report'):
            return
        for picking in self:
            picking.show_allocation = picking._get_show_allocation(picking.picking_type_id)

    @api.depends('picking_type_id', 'partner_id')
    def _compute_location_id(self):
        for picking in self:
            if picking.state != 'draft' or picking.return_id:
                continue
            picking = picking.with_company(picking.company_id)
            if picking.picking_type_id:
                if picking.picking_type_id.default_location_src_id:
                    location_id = picking.picking_type_id.default_location_src_id.id
                elif picking.partner_id:
                    location_id = picking.partner_id.property_stock_supplier.id
                else:
                    _customerloc, location_id = self.env['stock.warehouse']._get_partner_locations()

                if picking.picking_type_id.default_location_dest_id:
                    location_dest_id = picking.picking_type_id.default_location_dest_id.id
                elif picking.partner_id:
                    location_dest_id = picking.partner_id.property_stock_customer.id
                else:
                    location_dest_id, _supplierloc = self.env['stock.warehouse']._get_partner_locations()

                picking.location_id = location_id
                picking.location_dest_id = location_dest_id

    @api.depends('return_ids')
    def _compute_return_count(self):
        for picking in self:
            picking.return_count = len(picking.return_ids)

    def _get_show_allocation(self, picking_type_id):
        """ Helper method for computing "show_allocation" value.
        Separated out from _compute function so it can be reused in other models (e.g. batch).
        """
        if not picking_type_id or picking_type_id.code == 'outgoing':
            return False
        lines = self.move_ids.filtered(lambda m: m.product_id.type == 'product' and m.state != 'cancel')
        if lines:
            allowed_states = ['confirmed', 'partially_available', 'waiting']
            if self[0].state == 'done':
                allowed_states += ['assigned']
            wh_location_ids = self.env['stock.location']._search([('id', 'child_of', picking_type_id.warehouse_id.view_location_id.id), ('usage', '!=', 'supplier')])
            if self.env['stock.move'].search([
                ('state', 'in', allowed_states),
                ('product_qty', '>', 0),
                ('location_id', 'in', wh_location_ids),
                ('picking_id', 'not in', self.ids),
                ('product_id', 'in', lines.product_id.ids),
                '|', ('move_orig_ids', '=', False),
                     ('move_orig_ids', 'in', lines.ids)], limit=1):
                return True

    @api.model
    def _search_delay_alert_date(self, operator, value):
        late_stock_moves = self.env['stock.move'].search([('delay_alert_date', operator, value)])
        return [('move_ids', 'in', late_stock_moves.ids)]

    @api.onchange('picking_type_id', 'partner_id')
    def _onchange_picking_type(self):
        if self.picking_type_id and self.state == 'draft':
            self = self.with_company(self.company_id)
            (self.move_ids | self.move_ids_without_package).update({
                "picking_type_id": self.picking_type_id,  # The compute store doesn't work in case of One2many inverse (move_ids_without_package)
                "company_id": self.company_id,
            })
            for move in (self.move_ids | self.move_ids_without_package):
                if not move.product_id:
                    continue
                move.description_picking = move.product_id._get_description(move.picking_type_id)

        if self.partner_id and self.partner_id.picking_warn:
            if self.partner_id.picking_warn == 'no-message' and self.partner_id.parent_id:
                partner = self.partner_id.parent_id
            elif self.partner_id.picking_warn not in ('no-message', 'block') and self.partner_id.parent_id.picking_warn == 'block':
                partner = self.partner_id.parent_id
            else:
                partner = self.partner_id
            if partner.picking_warn != 'no-message':
                if partner.picking_warn == 'block':
                    self.partner_id = False
                return {'warning': {
                    'title': ("Warning for %s") % partner.name,
                    'message': partner.picking_warn_msg
                }}

    @api.onchange('location_id', 'location_dest_id')
    def _onchange_locations(self):
        (self.move_ids | self.move_ids_without_package).update({
            "location_id": self.location_id,
            "location_dest_id": self.location_dest_id
        })
        if self._origin.location_id != self.location_id and any(line.quantity for line in self.move_ids.move_line_ids):
            return {'warning': {
                    'title': 'Locations to update',
                    'message': _("You might want to update the locations of this transfer's operations")
                    }
            }

    @api.model_create_multi
    def create(self, vals_list):
        scheduled_dates = []
        for vals in vals_list:
            defaults = self.default_get(['name', 'picking_type_id'])
            picking_type = self.env['stock.picking.type'].browse(vals.get('picking_type_id', defaults.get('picking_type_id')))
            if vals.get('name', '/') == '/' and defaults.get('name', '/') == '/' and vals.get('picking_type_id', defaults.get('picking_type_id')):
                if picking_type.sequence_id:
                    vals['name'] = picking_type.sequence_id.next_by_id()

            # make sure to write `schedule_date` *after* the `stock.move` creation in
            # order to get a determinist execution of `_set_scheduled_date`
            scheduled_dates.append(vals.pop('scheduled_date', False))

        pickings = super().create(vals_list)

        for picking, scheduled_date in zip(pickings, scheduled_dates):
            if scheduled_date:
                picking.with_context(mail_notrack=True).write({'scheduled_date': scheduled_date})
        pickings._autoconfirm_picking()

        for picking, vals in zip(pickings, vals_list):
            # set partner as follower
            if vals.get('partner_id'):
                if picking.location_id.usage == 'supplier' or picking.location_dest_id.usage == 'customer':
                    picking.message_subscribe([vals.get('partner_id')])
            if vals.get('picking_type_id'):
                for move in picking.move_ids:
                    if not move.description_picking:
                        move.description_picking = move.product_id.with_context(lang=move._get_lang())._get_description(move.picking_id.picking_type_id)
        return pickings

    def write(self, vals):
        if vals.get('picking_type_id') and any(picking.state != 'draft' for picking in self):
            raise UserError(_("Changing the operation type of this record is forbidden at this point."))
        # set partner as a follower and unfollow old partner
        if vals.get('partner_id'):
            for picking in self:
                if picking.location_id.usage == 'supplier' or picking.location_dest_id.usage == 'customer':
                    if picking.partner_id:
                        picking.message_unsubscribe(picking.partner_id.ids)
                    picking.message_subscribe([vals.get('partner_id')])
        res = super(Picking, self).write(vals)
        if vals.get('signature'):
            for picking in self:
                picking._attach_sign()
        # Change locations of moves if those of the picking change
        after_vals = {}
        if vals.get('location_id'):
            after_vals['location_id'] = vals['location_id']
        if vals.get('location_dest_id'):
            after_vals['location_dest_id'] = vals['location_dest_id']
        if 'partner_id' in vals:
            after_vals['partner_id'] = vals['partner_id']
        if after_vals:
            self.move_ids.filtered(lambda move: not move.scrapped).write(after_vals)
        if vals.get('move_ids') or vals.get('move_ids_without_package'):
            self._autoconfirm_picking()

        return res

    def unlink(self):
        self.move_ids._action_cancel()
        self.with_context(prefetch_fields=False).move_ids.unlink()  # Checks if moves are not done
        return super(Picking, self).unlink()

    def do_print_picking(self):
        self.write({'printed': True})
        return self.env.ref('stock.action_report_picking').report_action(self)

    def should_print_delivery_address(self):
        self.ensure_one()
        return self.move_ids and self.move_ids[0].partner_id and self._is_to_external_location()

    def _is_to_external_location(self):
        self.ensure_one()
        return self.picking_type_code == 'outgoing'

    def action_confirm(self):
        self._check_company()
        self.mapped('package_level_ids').filtered(lambda pl: pl.state == 'draft' and not pl.move_ids)._generate_moves()
        # call `_action_confirm` on every draft move
        self.move_ids.filtered(lambda move: move.state == 'draft')._action_confirm()

        # run scheduler for moves forecasted to not have enough in stock
        self.move_ids.filtered(lambda move: move.state not in ('draft', 'cancel', 'done'))._trigger_scheduler()
        return True

    def action_assign(self):
        """ Check availability of picking moves.
        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        @return: True
        """
        self.mapped('package_level_ids').filtered(lambda pl: pl.state == 'draft' and not pl.move_ids)._generate_moves()
        self.filtered(lambda picking: picking.state == 'draft').action_confirm()
        moves = self.move_ids.filtered(lambda move: move.state not in ('draft', 'cancel', 'done')).sorted(
            key=lambda move: (-int(move.priority), not bool(move.date_deadline), move.date_deadline, move.date, move.id)
        )
        if not moves:
            raise UserError(_('Nothing to check the availability for.'))
        # If a package level is done when confirmed its location can be different than where it will be reserved.
        # So we remove the move lines created when confirmed to set quantity done to the new reserved ones.
        package_level_done = self.mapped('package_level_ids').filtered(lambda pl: pl.is_done and pl.state == 'confirmed')
        package_level_done.write({'is_done': False})
        moves._action_assign()
        package_level_done.write({'is_done': True})

        return True

    def action_cancel(self):
        self.move_ids._action_cancel()
        self.write({'is_locked': True})
        self.filtered(lambda x: not x.move_ids).state = 'cancel'
        return True

    def action_detailed_operations(self):
        view_id = self.env.ref('stock.view_stock_move_line_detailed_operation_tree').id
        return {
            'name': _('Detailed Operations'),
            'view_mode': 'tree',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move.line',
            'views': [(view_id, 'tree')],
            'domain': [('id', 'in', self.move_line_ids.ids)],
            'context': {
                'default_picking_id': self.id,
                'default_location_id': self.location_id.id,
                'default_location_dest_id': self.location_dest_id.id,
                'default_company_id': self.company_id.id,
                'show_lots_text': self.show_lots_text,
                'picking_code': self.picking_type_code,
            }
        }

    def _action_done(self):
        """Call `_action_done` on the `stock.move` of the `stock.picking` in `self`.
        This method makes sure every `stock.move.line` is linked to a `stock.move` by either
        linking them to an existing one or a newly created one.

        If the context key `cancel_backorder` is present, backorders won't be created.

        :return: True
        :rtype: bool
        """
        self._check_company()

        todo_moves = self.move_ids.filtered(lambda self: self.state in ['draft', 'waiting', 'partially_available', 'assigned', 'confirmed'])
        for picking in self:
            if picking.owner_id:
                picking.move_ids.write({'restrict_partner_id': picking.owner_id.id})
                picking.move_line_ids.write({'owner_id': picking.owner_id.id})
        todo_moves._action_done(cancel_backorder=self.env.context.get('cancel_backorder'))
        self.write({'date_done': fields.Datetime.now(), 'priority': '0'})

        # if incoming/internal moves make other confirmed/partially_available moves available, assign them
        done_incoming_moves = self.filtered(lambda p: p.picking_type_id.code in ('incoming', 'internal')).move_ids.filtered(lambda m: m.state == 'done')
        done_incoming_moves._trigger_assign()

        self._send_confirmation_email()
        return True

    def _send_confirmation_email(self):
        subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment')
        for stock_pick in self.filtered(lambda p: p.company_id.stock_move_email_validation and p.picking_type_id.code == 'outgoing'):
            delivery_template = stock_pick.company_id.stock_mail_confirmation_template_id
            stock_pick.with_context(force_send=True).message_post_with_source(
                delivery_template,
                email_layout_xmlid='mail.mail_notification_light',
                subtype_id=subtype_id,
            )

    def _check_move_lines_map_quant_package(self, package):
        return package._check_move_lines_map_quant(self.move_line_ids.filtered(lambda ml: ml.package_id == package and ml.product_id.type == 'product'))

    def _get_entire_pack_location_dest(self, move_line_ids):
        location_dest_ids = move_line_ids.mapped('location_dest_id')
        if len(location_dest_ids) > 1:
            return False
        return location_dest_ids.id

    def _check_entire_pack(self):
        """ This function check if entire packs are moved in the picking"""
        for package in self.move_line_ids.package_id:
            pickings = self.move_line_ids.filtered(lambda ml: ml.package_id == package).picking_id
            if pickings._check_move_lines_map_quant_package(package):
                package_level_ids = pickings.package_level_ids.filtered(lambda pl: pl.package_id == package)
                move_lines_to_pack = pickings.move_line_ids.filtered(lambda ml: ml.package_id == package and not ml.result_package_id and ml.state not in ('done', 'cancel'))
                if not package_level_ids:
                    if len(pickings) == 1:
                        package_location = pickings._get_entire_pack_location_dest(move_lines_to_pack) or pickings.location_dest_id.id
                        self.env['stock.package_level'].create({
                            'picking_id': pickings.id,
                            'package_id': package.id,
                            'location_id': package.location_id.id,
                            'location_dest_id': package_location,
                            'move_line_ids': [(6, 0, move_lines_to_pack.ids)],
                            'company_id': pickings.company_id.id,
                        })
                    # Propagate the result package in the next move for disposable packages only.
                    if package.package_use == 'disposable':
                        move_lines_to_pack.write({'result_package_id': package.id})
                else:
                    move_lines_in_package_level = move_lines_to_pack.filtered(lambda ml: ml.move_id.package_level_id)
                    move_lines_without_package_level = move_lines_to_pack - move_lines_in_package_level
                    for ml in move_lines_in_package_level:
                        ml.write({
                            'result_package_id': package.id,
                            'package_level_id': ml.move_id.package_level_id.id,
                        })
                    move_lines_without_package_level.write({
                        'result_package_id': package.id,
                        'package_level_id': package_level_ids[0].id,
                    })
                    for pl in package_level_ids:
                        pl.location_dest_id = pickings._get_entire_pack_location_dest(pl.move_line_ids) or pickings.location_dest_id.id
                    for move in move_lines_to_pack.move_id:
                        if all(line.package_level_id for line in move.move_line_ids) \
                                and len(move.move_line_ids.package_level_id) == 1:
                            move.package_level_id = move.move_line_ids.package_level_id

    def _get_lot_move_lines_for_sanity_check(self, none_done_picking_ids, separate_pickings=True):
        """ Get all move_lines with tracked products that need to be checked over in the sanity check.
            :param none_done_picking_ids: Set of all pickings ids that have no quantity set on any move_line.
            :param separate_pickings: Indicates if pickings should be checked independently for lot/serial numbers or not.
        """
        def get_relevant_move_line_ids(none_done_picking_ids, picking):
            # Get all move_lines if picking has no quantity set, otherwise only get the move_lines with some quantity set.
            if picking.id in none_done_picking_ids:
                return picking.move_line_ids.filtered(lambda ml: ml.product_id and ml.product_id.tracking != 'none').ids
            else:
                return get_line_with_done_qty_ids(picking.move_line_ids)

        def get_line_with_done_qty_ids(move_lines):
            # Get only move_lines that has some quantity set.
            return move_lines.filtered(lambda ml: ml.product_id and ml.product_id.tracking != 'none' and float_compare(ml.quantity, 0, precision_rounding=ml.product_uom_id.rounding)).ids

        if separate_pickings:
            # If pickings are checked independently, get full/partial move_lines depending if each picking has no quantity set.
            lines_to_check_ids = [line_id for picking in self for line_id in get_relevant_move_line_ids(none_done_picking_ids, picking)]
        else:
            # If pickings are checked as one (like in a batch), then get only the move_lines with quantity across all pickings if there is at least one.
            if any(picking.id not in none_done_picking_ids for picking in self):
                lines_to_check_ids = get_line_with_done_qty_ids(self.move_line_ids)
            else:
                lines_to_check_ids = self.move_line_ids.filtered(lambda ml: ml.product_id and ml.product_id.tracking != 'none').ids

        return self.env['stock.move.line'].browse(lines_to_check_ids)

    def _sanity_check(self, separate_pickings=True):
        """ Sanity check for `button_validate()`
            :param separate_pickings: Indicates if pickings should be checked independently for lot/serial numbers or not.
        """
        pickings_without_lots = self.browse()
        products_without_lots = self.env['product.product']
        pickings_without_moves = self.filtered(lambda p: not p.move_ids and not p.move_line_ids)
        precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        no_quantities_done_ids = set()
        pickings_without_quantities = self.env['stock.picking']
        for picking in self:
            if all(float_is_zero(move.quantity, precision_digits=precision_digits) for move in picking.move_ids.filtered(lambda m: m.state not in ('done', 'cancel'))):
                pickings_without_quantities |= picking

        pickings_using_lots = self.filtered(lambda p: p.picking_type_id.use_create_lots or p.picking_type_id.use_existing_lots)
        if pickings_using_lots:
            lines_to_check = pickings_using_lots._get_lot_move_lines_for_sanity_check(no_quantities_done_ids, separate_pickings)
            for line in lines_to_check:
                if not line.lot_name and not line.lot_id:
                    pickings_without_lots |= line.picking_id
                    products_without_lots |= line.product_id

        if not self._should_show_transfers():
            if pickings_without_moves:
                raise UserError(_("You can’t validate an empty transfer. Please add some products to move before proceeding."))
            if pickings_without_quantities:
                raise UserError(self._get_without_quantities_error_message())
            if pickings_without_lots:
                raise UserError(_('You need to supply a Lot/Serial number for products %s.', ', '.join(products_without_lots.mapped('display_name'))))
        else:
            message = ""
            if pickings_without_moves:
                message += _('Transfers %s: Please add some items to move.', ', '.join(pickings_without_moves.mapped('name')))
            if pickings_without_lots:
                message += _('\n\nTransfers %s: You need to supply a Lot/Serial number for products %s.', ', '.join(pickings_without_lots.mapped('name')), ', '.join(products_without_lots.mapped('display_name')))
            if message:
                raise UserError(message.lstrip())

    def do_unreserve(self):
        self.move_ids._do_unreserve()
        self.package_level_ids.filtered(lambda p: not p.move_ids).unlink()

    def button_validate(self):
        draft_picking = self.filtered(lambda p: p.state == 'draft')
        draft_picking.action_confirm()
        for move in draft_picking.move_ids:
            if float_is_zero(move.quantity, precision_rounding=move.product_uom.rounding) and\
               not float_is_zero(move.product_uom_qty, precision_rounding=move.product_uom.rounding):
                move.quantity = move.product_uom_qty

        # Sanity checks.
        if not self.env.context.get('skip_sanity_check', False):
            self._sanity_check()
        self.message_subscribe([self.env.user.partner_id.id])

        # Run the pre-validation wizards. Processing a pre-validation wizard should work on the
        # moves and/or the context and never call `_action_done`.
        if not self.env.context.get('button_validate_picking_ids'):
            self = self.with_context(button_validate_picking_ids=self.ids)
        res = self._pre_action_done_hook()
        if res is not True:
            return res

        # Call `_action_done`.
        pickings_not_to_backorder = self.filtered(lambda p: p.picking_type_id.create_backorder == 'never')
        if self.env.context.get('picking_ids_not_to_backorder'):
            pickings_not_to_backorder |= self.browse(self.env.context['picking_ids_not_to_backorder']).filtered(
                lambda p: p.picking_type_id.create_backorder != 'always'
            )
        pickings_to_backorder = self - pickings_not_to_backorder
        pickings_not_to_backorder.with_context(cancel_backorder=True)._action_done()
        pickings_to_backorder.with_context(cancel_backorder=False)._action_done()
        report_actions = self._get_autoprint_report_actions()
        another_action = False
        if self.user_has_groups('stock.group_reception_report'):
            pickings_show_report = self.filtered(lambda p: p.picking_type_id.auto_show_reception_report)
            lines = pickings_show_report.move_ids.filtered(lambda m: m.product_id.type == 'product' and m.state != 'cancel' and m.quantity and not m.move_dest_ids)
            if lines:
                # don't show reception report if all already assigned/nothing to assign
                wh_location_ids = self.env['stock.location']._search([('id', 'child_of', pickings_show_report.picking_type_id.warehouse_id.view_location_id.ids), ('usage', '!=', 'supplier')])
                if self.env['stock.move'].search([
                        ('state', 'in', ['confirmed', 'partially_available', 'waiting', 'assigned']),
                        ('product_qty', '>', 0),
                        ('location_id', 'in', wh_location_ids),
                        ('move_orig_ids', '=', False),
                        ('picking_id', 'not in', pickings_show_report.ids),
                        ('product_id', 'in', lines.product_id.ids)], limit=1):
                    action = pickings_show_report.action_view_reception_report()
                    action['context'] = {'default_picking_ids': pickings_show_report.ids}
                    if not report_actions:
                        return action
                    another_action = action
        if report_actions:
            return {
                'type': 'ir.actions.client',
                'tag': 'do_multi_print',
                'params': {
                    'reports': report_actions,
                    'anotherAction': another_action,
                }
            }
        return True

    def _pre_action_done_hook(self):
        for picking in self:
            if all(not move.picked for move in picking.move_ids):
                picking.move_ids.picked = True
        if not self.env.context.get('skip_backorder'):
            pickings_to_backorder = self._check_backorder()
            if pickings_to_backorder:
                return pickings_to_backorder._action_generate_backorder_wizard(show_transfers=self._should_show_transfers())
        return True

    def _should_show_transfers(self):
        """Whether the different transfers should be displayed on the pre action done wizards."""
        return len(self) > 1

    def _get_without_quantities_error_message(self):
        """ Returns the error message raised in validation if no quantities are reserved.
        The purpose of this method is to be overridden in case we want to adapt this message.

        :return: Translated error message
        :rtype: str
        """
        return _(
            'You cannot validate a transfer if no quantities are reserved. '
            'To force the transfer, encode quantities.'
        )

    def _action_generate_backorder_wizard(self, show_transfers=False):
        view = self.env.ref('stock.view_backorder_confirmation')
        return {
            'name': _('Create Backorder?'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock.backorder.confirmation',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': dict(self.env.context, default_show_transfers=show_transfers, default_pick_ids=[(4, p.id) for p in self]),
        }

    def action_toggle_is_locked(self):
        self.ensure_one()
        self.is_locked = not self.is_locked
        return True

    def _check_backorder(self):
        prec = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        backorder_pickings = self.browse()
        for picking in self:
            if picking.picking_type_id.create_backorder != 'ask':
                continue
            if any(
                    (move.product_uom_qty and not move.picked) or
                    float_compare(move._get_picked_quantity(), move.product_uom_qty, precision_digits=prec) < 0
                    for move in picking.move_ids
                    if move.state != 'cancel'
            ):
                backorder_pickings |= picking
        return backorder_pickings

    def _autoconfirm_picking(self):
        """ Automatically run `action_confirm` on `self` if one of the
        picking's move was added after the initial
        call to `action_confirm`. Note that `action_confirm` will only work on draft moves.
        """
        for picking in self:
            if picking.state in ('done', 'cancel'):
                continue
            if not picking.move_ids and not picking.package_level_ids:
                continue
            if any(move.additional for move in picking.move_ids):
                picking.action_confirm()
        to_confirm = self.move_ids.filtered(lambda m: m.state == 'draft' and m.quantity)
        to_confirm._action_confirm()

    def _create_backorder(self):
        """ This method is called when the user chose to create a backorder. It will create a new
        picking, the backorder, and move the stock.moves that are not `done` or `cancel` into it.
        """
        backorders = self.env['stock.picking']
        bo_to_assign = self.env['stock.picking']
        for picking in self:
            moves_to_backorder = picking.move_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
            moves_to_backorder._recompute_state()
            if moves_to_backorder:
                backorder_picking = picking.copy({
                    'name': '/',
                    'move_ids': [],
                    'move_line_ids': [],
                    'backorder_id': picking.id
                })
                picking.message_post(
                    body=_('The backorder %s has been created.', backorder_picking._get_html_link())
                )
                moves_to_backorder.write({'picking_id': backorder_picking.id})
                moves_to_backorder.move_line_ids.package_level_id.write({'picking_id': backorder_picking.id})
                # moves_to_backorder._do_unreserve()
                moves_to_backorder.mapped('move_line_ids').write({'picking_id': backorder_picking.id})
                backorders |= backorder_picking
                if backorder_picking.picking_type_id.reservation_method == 'at_confirm':
                    bo_to_assign |= backorder_picking
        if bo_to_assign:
            bo_to_assign.action_assign()
        return backorders

    def _log_activity_get_documents(self, orig_obj_changes, stream_field, stream, groupby_method=False):
        """ Generic method to log activity. To use with
        _log_activity method. It either log on uppermost
        ongoing documents or following documents. This method
        find all the documents and responsible for which a note
        has to be log. It also generate a rendering_context in
        order to render a specific note by documents containing
        only the information relative to the document it. For example
        we don't want to notify a picking on move that it doesn't
        contain.

        :param orig_obj_changes dict: contain a record as key and the
        change on this record as value.
        eg: {'move_id': (new product_uom_qty, old product_uom_qty)}
        :param stream_field string: It has to be a field of the
        records that are register in the key of 'orig_obj_changes'
        eg: 'move_dest_ids' if we use move as record (previous example)
            - 'UP' if we want to log on the upper most ongoing
            documents.
            - 'DOWN' if we want to log on following documents.
        :param groupby_method: Only need when
        stream is 'DOWN', it should group by tuple(object on
        which the activity is log, the responsible for this object)
        """
        if self.env.context.get('skip_activity'):
            return {}
        move_to_orig_object_rel = {co: ooc for ooc in orig_obj_changes.keys() for co in ooc[stream_field]}
        origin_objects = self.env[list(orig_obj_changes.keys())[0]._name].concat(*list(orig_obj_changes.keys()))
        # The purpose here is to group each destination object by
        # (document to log, responsible) no matter the stream direction.
        # example:
        # {'(delivery_picking_1, admin)': stock.move(1, 2)
        #  '(delivery_picking_2, admin)': stock.move(3)}
        visited_documents = {}
        if stream == 'DOWN':
            if groupby_method:
                grouped_moves = groupby(origin_objects.mapped(stream_field), key=groupby_method)
            else:
                raise AssertionError('You have to define a groupby method and pass them as arguments.')
        elif stream == 'UP':
            # When using upstream document it is required to define
            # _get_upstream_documents_and_responsibles on
            # destination objects in order to ascend documents.
            grouped_moves = {}
            for visited_move in origin_objects.mapped(stream_field):
                for document, responsible, visited in visited_move._get_upstream_documents_and_responsibles(self.env[visited_move._name]):
                    if grouped_moves.get((document, responsible)):
                        grouped_moves[(document, responsible)] |= visited_move
                        visited_documents[(document, responsible)] |= visited
                    else:
                        grouped_moves[(document, responsible)] = visited_move
                        visited_documents[(document, responsible)] = visited
            grouped_moves = grouped_moves.items()
        else:
            raise AssertionError('Unknown stream.')

        documents = {}
        for (parent, responsible), moves in grouped_moves:
            if not parent:
                continue
            moves = self.env[moves[0]._name].concat(*moves)
            # Get the note
            rendering_context = {move: (orig_object, orig_obj_changes[orig_object]) for move in moves for orig_object in move_to_orig_object_rel[move]}
            if visited_documents:
                documents[(parent, responsible)] = rendering_context, visited_documents.values()
            else:
                documents[(parent, responsible)] = rendering_context
        return documents

    def _log_activity(self, render_method, documents):
        """ Log a note for each documents, responsible pair in
        documents passed as argument. The render_method is then
        call in order to use a template and render it with a
        rendering_context.

        :param documents dict: A tuple (document, responsible) as key.
        An activity will be log by key. A rendering_context as value.
        If used with _log_activity_get_documents. In 'DOWN' stream
        cases the rendering_context will be a dict with format:
        {'stream_object': ('orig_object', new_qty, old_qty)}
        'UP' stream will add all the documents browsed in order to
        get the final/upstream document present in the key.
        :param render_method method: a static function that will generate
        the html note to log on the activity. The render_method should
        use the args:
            - rendering_context dict: value of the documents argument
        the render_method should return a string with an html format
        :param stream string:
        """
        for (parent, responsible), rendering_context in documents.items():
            note = render_method(rendering_context)
            parent.activity_schedule(
                'mail.mail_activity_data_warning',
                date.today(),
                note=note,
                user_id=responsible.id or SUPERUSER_ID
            )

    def _log_less_quantities_than_expected(self, moves):
        """ Log an activity on picking that follow moves. The note
        contains the moves changes and all the impacted picking.

        :param dict moves: a dict with a move as key and tuple with
        new and old quantity as value. eg: {move_1 : (4, 5)}
        """
        def _keys_in_groupby(move):
            """ group by picking and the responsible for the product the
            move.
            """
            return (move.picking_id, move.product_id.responsible_id)

        def _render_note_exception_quantity(rendering_context):
            """ :param rendering_context:
            {'move_dest': (move_orig, (new_qty, old_qty))}
            """
            origin_moves = self.env['stock.move'].browse([move.id for move_orig in rendering_context.values() for move in move_orig[0]])
            origin_picking = origin_moves.mapped('picking_id')
            move_dest_ids = self.env['stock.move'].concat(*rendering_context.keys())
            impacted_pickings = origin_picking._get_impacted_pickings(move_dest_ids) - move_dest_ids.mapped('picking_id')
            values = {
                'origin_picking': origin_picking,
                'moves_information': rendering_context.values(),
                'impacted_pickings': impacted_pickings,
            }
            return self.env['ir.qweb']._render('stock.exception_on_picking', values)

        documents = self._log_activity_get_documents(moves, 'move_dest_ids', 'DOWN', _keys_in_groupby)
        documents = self._less_quantities_than_expected_add_documents(moves, documents)
        self._log_activity(_render_note_exception_quantity, documents)

    def _less_quantities_than_expected_add_documents(self, moves, documents):
        return documents

    def _get_impacted_pickings(self, moves):
        """ This function is used in _log_less_quantities_than_expected
        the purpose is to notify a user with all the pickings that are
        impacted by an action on a chained move.
        param: 'moves' contain moves that belong to a common picking.
        return: all the pickings that contain a destination moves
        (direct and indirect) from the moves given as arguments.
        """

        def _explore(impacted_pickings, explored_moves, moves_to_explore):
            for move in moves_to_explore:
                if move not in explored_moves:
                    impacted_pickings |= move.picking_id
                    explored_moves |= move
                    moves_to_explore |= move.move_dest_ids
            moves_to_explore = moves_to_explore - explored_moves
            if moves_to_explore:
                return _explore(impacted_pickings, explored_moves, moves_to_explore)
            else:
                return impacted_pickings

        return _explore(self.env['stock.picking'], self.env['stock.move'], moves)

    def _pre_put_in_pack_hook(self, move_line_ids):
        return self._check_destinations(move_line_ids)

    def _check_destinations(self, move_line_ids):
        if len(move_line_ids.mapped('location_dest_id')) > 1:
            view_id = self.env.ref('stock.stock_package_destination_form_view').id
            wiz = self.env['stock.package.destination'].create({
                'picking_id': self.id,
                'location_dest_id': move_line_ids[0].location_dest_id.id,
            })
            return {
                'name': _('Choose destination location'),
                'view_mode': 'form',
                'res_model': 'stock.package.destination',
                'view_id': view_id,
                'views': [(view_id, 'form')],
                'type': 'ir.actions.act_window',
                'res_id': wiz.id,
                'target': 'new'
            }
        else:
            return {}

    def _put_in_pack(self, move_line_ids):
        package = self.env['stock.quant.package'].create({})
        package_type = move_line_ids.move_id.product_packaging_id.package_type_id
        if len(package_type) == 1:
            package.package_type_id = package_type
        if len(move_line_ids) == 1:
            default_dest_location = move_line_ids._get_default_dest_location()
            move_line_ids.location_dest_id = default_dest_location._get_putaway_strategy(
                product=move_line_ids.product_id,
                quantity=move_line_ids.quantity,
                package=package)
        move_line_ids.write({
            'result_package_id': package.id,
        })
        if len(self) == 1:
            self.env['stock.package_level'].create({
                'package_id': package.id,
                'picking_id': self.id,
                'location_id': False,
                'location_dest_id': move_line_ids.location_dest_id.id,
                'move_line_ids': [(6, 0, move_line_ids.ids)],
                'company_id': self.company_id.id,
            })
        return package

    def _post_put_in_pack_hook(self, package_id):
        if package_id and self.picking_type_id.auto_print_package_label:
            if self.picking_type_id.package_label_to_print == 'pdf':
                action = self.env.ref("stock.action_report_quant_package_barcode_small").report_action(package_id.id, config=False)
            elif self.picking_type_id.package_label_to_print == 'zpl':
                action = self.env.ref("stock.label_package_template").report_action(package_id.id, config=False)
            if action:
                action.update({'close_on_report_download': True})
                clean_action(action, self.env)
                return action
        return package_id

    def _package_move_lines(self):
        quantity_move_line_ids = self.move_line_ids.filtered(
            lambda ml:
                float_compare(ml.quantity, 0.0, precision_rounding=ml.product_uom_id.rounding) > 0 and
                not ml.result_package_id
        )
        move_line_ids = quantity_move_line_ids.filtered(lambda ml: ml.picked)
        if not move_line_ids:
            move_line_ids = quantity_move_line_ids
        return move_line_ids

    def action_put_in_pack(self):
        self.ensure_one()
        if self.state not in ('done', 'cancel'):
            move_line_ids = self._package_move_lines()
            if move_line_ids:
                res = self._pre_put_in_pack_hook(move_line_ids)
                if not res:
                    package = self._put_in_pack(move_line_ids)
                    self.action_assign()
                    return self._post_put_in_pack_hook(package)
                return res
            raise UserError(_("There is nothing eligible to put in a pack. Either there are no quantities to put in a pack or all products are already in a pack."))

    def button_scrap(self):
        self.ensure_one()
        view = self.env.ref('stock.stock_scrap_form_view2')
        products = self.env['product.product']
        for move in self.move_ids:
            if move.state not in ('draft', 'cancel') and move.product_id.type in ('product', 'consu'):
                products |= move.product_id
        return {
            'name': _('Scrap Products'),
            'view_mode': 'form',
            'res_model': 'stock.scrap',
            'view_id': view.id,
            'views': [(view.id, 'form')],
            'type': 'ir.actions.act_window',
            'context': {'default_picking_id': self.id, 'product_ids': products.ids, 'default_company_id': self.company_id.id},
            'target': 'new',
        }

    def action_see_move_scrap(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_stock_scrap")
        scraps = self.env['stock.scrap'].search([('picking_id', '=', self.id)])
        action['domain'] = [('id', 'in', scraps.ids)]
        action['context'] = dict(self._context, create=False)
        return action

    def action_see_packages(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_package_view")
        packages = self.move_line_ids.mapped('result_package_id')
        action['domain'] = [('id', 'in', packages.ids)]
        action['context'] = {'picking_id': self.id}
        return action

    def action_picking_move_tree(self):
        action = self.env["ir.actions.actions"]._for_xml_id("stock.stock_move_action")
        action['views'] = [
            (self.env.ref('stock.view_picking_move_tree').id, 'tree'),
        ]
        action['context'] = self.env.context
        action['domain'] = [('picking_id', 'in', self.ids)]
        return action

    def action_view_reception_report(self):
        return self.env["ir.actions.actions"]._for_xml_id("stock.stock_reception_action")

    def action_open_label_layout(self):
        view = self.env.ref('stock.product_label_layout_form_picking')
        return {
            'name': _('Choose Labels Layout'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.label.layout',
            'views': [(view.id, 'form')],
            'target': 'new',
            'context': {
                'default_product_ids': self.move_ids.product_id.ids,
                'default_move_ids': self.move_ids.ids,
                'default_move_quantity': 'move'},
        }

    def action_open_label_type(self):
        if self.user_has_groups('stock.group_production_lot') and self.move_line_ids.lot_id:
            view = self.env.ref('stock.picking_label_type_form')
            return {
                'name': _('Choose Type of Labels To Print'),
                'type': 'ir.actions.act_window',
                'res_model': 'picking.label.type',
                'views': [(view.id, 'form')],
                'target': 'new',
                'context': {'default_picking_ids': self.ids},
            }
        return self.action_open_label_layout()

    def _attach_sign(self):
        """ Render the delivery report in pdf and attach it to the picking in `self`. """
        self.ensure_one()
        report = self.env['ir.actions.report']._render_qweb_pdf("stock.action_report_delivery", self.id)
        filename = "%s_signed_delivery_slip" % self.name
        if self.partner_id:
            message = _('Order signed by %s', self.partner_id.name)
        else:
            message = _('Order signed')
        self.message_post(
            attachments=[('%s.pdf' % filename, report[0])],
            body=message,
        )
        return True

    def action_see_returns(self):
        self.ensure_one()
        if len(self.return_ids) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "stock.picking",
                "views": [[False, "form"]],
                "res_id": self.return_ids.id
            }
        return {
            'name': _('Returns'),
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "views": [[False, "tree"], [False, "form"]],
            "domain": [('id', 'in', self.return_ids.ids)],
        }

    def _get_report_lang(self):
        return self.move_ids and self.move_ids[0].partner_id.lang or self.partner_id.lang or self.env.lang

    def _get_autoprint_report_actions(self):
        report_actions = []
        pickings_to_print = self.filtered(lambda p: p.picking_type_id.auto_print_delivery_slip)
        if pickings_to_print:
            action = self.env.ref("stock.action_report_delivery").report_action(pickings_to_print.ids, config=False)
            clean_action(action, self.env)
            report_actions.append(action)
        pickings_print_return_slip = self.filtered(lambda p: p.picking_type_id.auto_print_return_slip)
        if pickings_print_return_slip:
            action = self.env.ref("stock.return_label_report").report_action(pickings_print_return_slip.ids, config=False)
            clean_action(action, self.env)
            report_actions.append(action)

        if self.user_has_groups('stock.group_reception_report'):
            reception_reports_to_print = self.filtered(
                lambda p: p.picking_type_id.auto_print_reception_report
                          and p.picking_type_id.code != 'outgoing'
                          and p.move_ids.move_dest_ids
            )
            if reception_reports_to_print:
                action = self.env.ref('stock.stock_reception_report_action').report_action(reception_reports_to_print, config=False)
                clean_action(action, self.env)
                report_actions.append(action)
            reception_labels_to_print = self.filtered(lambda p: p.picking_type_id.auto_print_reception_report_labels and p.picking_type_id.code != 'outgoing')
            if reception_labels_to_print:
                moves_to_print = reception_labels_to_print.move_ids.move_dest_ids
                if moves_to_print:
                    # needs to be string to support python + js calls to report
                    quantities = ','.join(str(qty) for qty in moves_to_print.mapped(lambda m: math.ceil(m.product_uom_qty)))
                    data = {
                        'docids': moves_to_print.ids,
                        'quantity': quantities,
                    }
                    action = self.env.ref('stock.label_picking').report_action(moves_to_print, data=data, config=False)
                    clean_action(action, self.env)
                    report_actions.append(action)
        pickings_print_product_label = self.filtered(lambda p: p.picking_type_id.auto_print_product_labels)
        pickings_by_print_formats = pickings_print_product_label.grouped(lambda p: p.picking_type_id.product_label_format)
        for print_format in pickings_print_product_label.picking_type_id.mapped("product_label_format"):
            pickings = pickings_by_print_formats.get(print_format)
            wizard = self.env['product.label.layout'].create({
                'product_ids': pickings.move_ids.product_id.ids,
                'move_ids': pickings.move_ids.ids,
                'move_quantity': 'move',
                'print_format': pickings.picking_type_id.product_label_format,
            })
            action = wizard.process()
            if action:
                clean_action(action, self.env)
                report_actions.append(action)
        if self.user_has_groups('stock.group_production_lot'):
            pickings_print_lot_label = self.filtered(lambda p: p.picking_type_id.auto_print_lot_labels and p.move_line_ids.lot_id)
            pickings_by_print_formats = pickings_print_lot_label.grouped(lambda p: p.picking_type_id.lot_label_format)
            for print_format in pickings_print_lot_label.picking_type_id.mapped("lot_label_format"):
                pickings = pickings_by_print_formats.get(print_format)
                wizard = self.env['lot.label.layout'].create({
                    'move_line_ids': pickings.move_line_ids.ids,
                    'label_quantity': 'lots' if '_lots' in print_format else 'units',
                    'print_format': '4x12' if '4x12' in print_format else 'zpl',
                })
                action = wizard.process()
                if action:
                    clean_action(action, self.env)
                    report_actions.append(action)
        if self.user_has_groups('stock.group_tracking_lot'):
            pickings_print_packages = self.filtered(lambda p: p.picking_type_id.auto_print_packages and p.move_line_ids.result_package_id)
            if pickings_print_packages:
                action = self.env.ref("stock.action_report_picking_packages").report_action(pickings_print_packages.ids, config=False)
                clean_action(action, self.env)
                report_actions.append(action)
        return report_actions
