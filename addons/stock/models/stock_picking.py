# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import namedtuple
import json
import time

from itertools import groupby
from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round
from odoo.exceptions import UserError
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from operator import itemgetter


class PickingType(models.Model):
    _name = "stock.picking.type"
    _description = "The operation type determines the picking view"
    _order = 'sequence, id'

    name = fields.Char('Operation Types Name', required=True, translate=True)
    color = fields.Integer('Color')
    sequence = fields.Integer('Sequence', help="Used to order the 'All Operations' kanban view")
    sequence_id = fields.Many2one('ir.sequence', 'Reference Sequence', required=True)
    default_location_src_id = fields.Many2one(
        'stock.location', 'Default Source Location',
        help="This is the default source location when you create a picking manually with this operation type. It is possible however to change it or that the routes put another location. If it is empty, it will check for the supplier location on the partner. ")
    default_location_dest_id = fields.Many2one(
        'stock.location', 'Default Destination Location',
        help="This is the default destination location when you create a picking manually with this operation type. It is possible however to change it or that the routes put another location. If it is empty, it will check for the customer location on the partner. ")
    code = fields.Selection([('incoming', 'Vendors'), ('outgoing', 'Customers'), ('internal', 'Internal')], 'Type of Operation', required=True)
    return_picking_type_id = fields.Many2one('stock.picking.type', 'Operation Type for Returns')
    show_entire_packs = fields.Boolean('Allow moving packs', help="If checked, this shows the packs to be moved as a whole in the Operations tab all the time, even if there was no entire pack reserved.")
    warehouse_id = fields.Many2one(
        'stock.warehouse', 'Warehouse', ondelete='cascade',
        default=lambda self: self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1))
    active = fields.Boolean('Active', default=True)
    use_create_lots = fields.Boolean(
        'Create New Lots/Serial Numbers', default=True,
        help="If this is checked only, it will suppose you want to create new Lots/Serial Numbers, so you can provide them in a text field. ")
    use_existing_lots = fields.Boolean(
        'Use Existing Lots/Serial Numbers', default=True,
        help="If this is checked, you will be able to choose the Lots/Serial Numbers. You can also decide to not put lots in this operation type.  This means it will create stock with no lot or not put a restriction on the lot taken. ")
    show_operations = fields.Boolean(
        'Show Detailed Operations', default=False,
        help="If this checkbox is ticked, the pickings lines will represent detailed stock operations. If not, the picking lines will represent an aggregate of detailed stock operations.")
    show_reserved = fields.Boolean(
        'Show Reserved', default=True, help="If this checkbox is ticked, Odoo will show which products are reserved (lot/serial number, source location, source package).")

    # Statistics for the kanban view
    last_done_picking = fields.Char('Last 10 Done Pickings', compute='_compute_last_done_picking')
    count_picking_draft = fields.Integer(compute='_compute_picking_count')
    count_picking_ready = fields.Integer(compute='_compute_picking_count')
    count_picking = fields.Integer(compute='_compute_picking_count')
    count_picking_waiting = fields.Integer(compute='_compute_picking_count')
    count_picking_late = fields.Integer(compute='_compute_picking_count')
    count_picking_backorders = fields.Integer(compute='_compute_picking_count')
    rate_picking_late = fields.Integer(compute='_compute_picking_count')
    rate_picking_backorders = fields.Integer(compute='_compute_picking_count')

    barcode_nomenclature_id = fields.Many2one(
        'barcode.nomenclature', 'Barcode Nomenclature')

    @api.one
    def _compute_last_done_picking(self):
        # TDE TODO: true multi
        tristates = []
        for picking in self.env['stock.picking'].search([('picking_type_id', '=', self.id), ('state', '=', 'done')], order='date_done desc', limit=10):
            if picking.date_done > picking.date:
                tristates.insert(0, {'tooltip': picking.name or '' + ": " + _('Late'), 'value': -1})
            elif picking.backorder_id:
                tristates.insert(0, {'tooltip': picking.name or '' + ": " + _('Backorder exists'), 'value': 0})
            else:
                tristates.insert(0, {'tooltip': picking.name or '' + ": " + _('OK'), 'value': 1})
        self.last_done_picking = json.dumps(tristates)

    def _compute_picking_count(self):
        # TDE TODO count picking can be done using previous two
        domains = {
            'count_picking_draft': [('state', '=', 'draft')],
            'count_picking_waiting': [('state', 'in', ('confirmed', 'waiting'))],
            'count_picking_ready': [('state', '=', 'assigned')],
            'count_picking': [('state', 'in', ('assigned', 'waiting', 'confirmed'))],
            'count_picking_late': [('scheduled_date', '<', time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)), ('state', 'in', ('assigned', 'waiting', 'confirmed'))],
            'count_picking_backorders': [('backorder_id', '!=', False), ('state', 'in', ('confirmed', 'assigned', 'waiting'))],
        }
        for field in domains:
            data = self.env['stock.picking'].read_group(domains[field] +
                [('state', 'not in', ('done', 'cancel')), ('picking_type_id', 'in', self.ids)],
                ['picking_type_id'], ['picking_type_id'])
            count = {
                x['picking_type_id'][0]: x['picking_type_id_count']
                for x in data if x['picking_type_id']
            }
            for record in self:
                record[field] = count.get(record.id, 0)
        for record in self:
            record.rate_picking_late = record.count_picking and record.count_picking_late * 100 / record.count_picking or 0
            record.rate_picking_backorders = record.count_picking and record.count_picking_backorders * 100 / record.count_picking or 0

    def name_get(self):
        """ Display 'Warehouse_name: PickingType_name' """
        # TDE TODO remove context key support + update purchase
        res = []
        for picking_type in self:
            if self.env.context.get('special_shortened_wh_name'):
                if picking_type.warehouse_id:
                    name = picking_type.warehouse_id.name
                else:
                    name = _('Customer') + ' (' + picking_type.name + ')'
            elif picking_type.warehouse_id:
                name = picking_type.warehouse_id.name + ': ' + picking_type.name
            else:
                name = picking_type.name
            res.append((picking_type.id, name))
        return res

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('warehouse_id.name', operator, name)]
        picks = self.search(domain + args, limit=limit)
        return picks.name_get()

    @api.onchange('code')
    def onchange_picking_code(self):
        if self.code == 'incoming':
            self.default_location_src_id = self.env.ref('stock.stock_location_suppliers').id
            self.default_location_dest_id = self.env.ref('stock.stock_location_stock').id
        elif self.code == 'outgoing':
            self.default_location_src_id = self.env.ref('stock.stock_location_stock').id
            self.default_location_dest_id = self.env.ref('stock.stock_location_customers').id

    @api.onchange('show_operations')
    def onchange_show_operations(self):
        if self.show_operations is True:
            self.show_reserved = True

    def _get_action(self, action_xmlid):
        # TDE TODO check to have one view + custo in methods
        action = self.env.ref(action_xmlid).read()[0]
        if self:
            action['display_name'] = self.display_name
        return action

    def get_action_picking_tree_late(self):
        return self._get_action('stock.action_picking_tree_late')

    def get_action_picking_tree_backorder(self):
        return self._get_action('stock.action_picking_tree_backorder')

    def get_action_picking_tree_waiting(self):
        return self._get_action('stock.action_picking_tree_waiting')

    def get_action_picking_tree_ready(self):
        return self._get_action('stock.action_picking_tree_ready')

    def get_stock_picking_action_picking_type(self):
        return self._get_action('stock.stock_picking_action_picking_type')


class Picking(models.Model):
    _name = "stock.picking"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Transfer"
    _order = "priority desc, date asc, id desc"

    name = fields.Char(
        'Reference', default='/',
        copy=False,  index=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    origin = fields.Char(
        'Source Document', index=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="Reference of the document")
    note = fields.Text('Notes')

    backorder_id = fields.Many2one(
        'stock.picking', 'Back Order of',
        copy=False, index=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="If this shipment was split, then this field links to the shipment which contains the already processed part.")

    move_type = fields.Selection([
        ('direct', 'As soon as possible'), ('one', 'When all products are ready')], 'Shipping Policy',
        default='direct', required=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="It specifies goods to be deliver partially or all at once")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, track_visibility='onchange',
        help=" * Draft: not confirmed yet and will not be scheduled until confirmed.\n"
             " * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows).\n"
             " * Waiting: if it is not ready to be sent because the required products could not be reserved.\n"
             " * Ready: products are reserved and ready to be sent. If the shipping policy is 'As soon as possible' this happens as soon as anything is reserved.\n"
             " * Done: has been processed, can't be modified or cancelled anymore.\n"
             " * Cancelled: has been cancelled, can't be confirmed anymore.")

    group_id = fields.Many2one(
        'procurement.group', 'Procurement Group',
        readonly=True, related='move_lines.group_id', store=True)

    priority = fields.Selection(
        PROCUREMENT_PRIORITIES, string='Priority',
        compute='_compute_priority', inverse='_set_priority', store=True,
        # default='1', required=True,  # TDE: required, depending on moves ? strange
        index=True, track_visibility='onchange',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="Priority for this picking. Setting manually a value here would set it as priority for all the moves")
    scheduled_date = fields.Datetime(
        'Scheduled Date', compute='_compute_scheduled_date', inverse='_set_scheduled_date', store=True,
        index=True, track_visibility='onchange',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="Scheduled time for the first part of the shipment to be processed. Setting manually a value here would set it as expected date for all the stock moves.")
    date = fields.Datetime(
        'Creation Date',
        default=fields.Datetime.now, index=True, track_visibility='onchange',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="Creation Date, usually the time of the order")
    date_done = fields.Datetime('Date of Transfer', copy=False, readonly=True, help="Completion Date of Transfer")

    location_id = fields.Many2one(
        'stock.location', "Source Location",
        default=lambda self: self.env['stock.picking.type'].browse(self._context.get('default_picking_type_id')).default_location_src_id,
        readonly=True, required=True,
        states={'draft': [('readonly', False)]})
    location_dest_id = fields.Many2one(
        'stock.location', "Destination Location",
        default=lambda self: self.env['stock.picking.type'].browse(self._context.get('default_picking_type_id')).default_location_dest_id,
        readonly=True, required=True,
        states={'draft': [('readonly', False)]})
    move_lines = fields.One2many('stock.move', 'picking_id', string="Stock Moves", copy=True)
    has_scrap_move = fields.Boolean(
        'Has Scrap Moves', compute='_has_scrap_move')
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type',
        required=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    picking_type_code = fields.Selection([
        ('incoming', 'Vendors'),
        ('outgoing', 'Customers'),
        ('internal', 'Internal')], related='picking_type_id.code',
        readonly=True)
    picking_type_entire_packs = fields.Boolean(related='picking_type_id.show_entire_packs',
        readonly=True)

    partner_id = fields.Many2one(
        'res.partner', 'Partner',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get('stock.picking'),
        index=True, required=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})

    move_line_ids = fields.One2many('stock.move.line', 'picking_id', 'Operations')

    move_line_exist = fields.Boolean(
        'Has Pack Operations', compute='_compute_move_line_exist',
        help='Check the existence of pack operation on the picking')

    has_packages = fields.Boolean(
        'Has Packages', compute='_compute_has_packages',
        help='Check the existence of destination packages on move lines')

    entire_package_ids = fields.One2many('stock.quant.package', compute='_compute_entire_package_ids',
                                         help='Those are the entire packages of a picking shown in the view of operations')
    entire_package_detail_ids = fields.One2many('stock.quant.package', compute='_compute_entire_package_ids',
                                                help='Those are the entire packages of a picking shown in the view of detailed operations')

    show_check_availability = fields.Boolean(
        compute='_compute_show_check_availability',
        help='Technical field used to compute whether the check availability button should be shown.')
    show_mark_as_todo = fields.Boolean(
        compute='_compute_show_mark_as_todo',
        help='Technical field used to compute whether the mark as todo button should be shown.')
    show_validate = fields.Boolean(
        compute='_compute_show_validate',
        help='Technical field used to compute whether the validate should be shown.')

    owner_id = fields.Many2one(
        'res.partner', 'Owner',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="Default Owner")
    printed = fields.Boolean('Printed')
    is_locked = fields.Boolean(default=True, help='When the picking is not done this allows changing the '
                               'initial demand. When the picking is done this allows '
                               'changing the done quantities.')
    # Used to search on pickings
    product_id = fields.Many2one('product.product', 'Product', related='move_lines.product_id')
    show_operations = fields.Boolean(compute='_compute_show_operations')
    show_lots_text = fields.Boolean(compute='_compute_show_lots_text')

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Reference must be unique per company!'),
    ]

    @api.depends('picking_type_id.show_operations')
    def _compute_show_operations(self):
        for picking in self:
            if self.env.context.get('force_detailed_view'):
                picking.show_operations = True
                break
            if picking.picking_type_id.show_operations:
                if (picking.state == 'draft' and not self.env.context.get('planned_picking')) or picking.state != 'draft':
                    picking.show_operations = True
                else:
                    picking.show_operations = False
            else:
                picking.show_operations = False

    @api.depends('move_line_ids', 'picking_type_id.use_create_lots', 'picking_type_id.use_existing_lots', 'state')
    def _compute_show_lots_text(self):
        group_production_lot_enabled = self.user_has_groups('stock.group_production_lot')
        for picking in self:
            if not picking.move_line_ids:
                picking.show_lots_text = False
            elif group_production_lot_enabled and picking.picking_type_id.use_create_lots \
                    and not picking.picking_type_id.use_existing_lots and picking.state != 'done':
                picking.show_lots_text = True
            else:
                picking.show_lots_text = False

    @api.depends('move_type', 'move_lines.state', 'move_lines.picking_id')
    @api.one
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
        - Done: if the picking is done.
        - Cancelled: if the picking is cancelled
        '''
        if not self.move_lines:
            self.state = 'draft'
        elif any(move.state == 'draft' for move in self.move_lines):  # TDE FIXME: should be all ?
            self.state = 'draft'
        elif all(move.state == 'cancel' for move in self.move_lines):
            self.state = 'cancel'
        elif all(move.state in ['cancel', 'done'] for move in self.move_lines):
            self.state = 'done'
        else:
            relevant_move_state = self.move_lines._get_relevant_state_among_moves()
            if relevant_move_state == 'partially_available':
                self.state = 'assigned'
            else:
                self.state = relevant_move_state

    @api.one
    @api.depends('move_lines.priority')
    def _compute_priority(self):
        if self.mapped('move_lines'):
            priorities = [priority for priority in self.mapped('move_lines.priority') if priority] or ['1']
            self.priority = max(priorities)
        else:
            self.priority = '1'

    @api.one
    def _set_priority(self):
        self.move_lines.write({'priority': self.priority})

    @api.one
    @api.depends('move_lines.date_expected')
    def _compute_scheduled_date(self):
        if self.move_type == 'direct':
            self.scheduled_date = min(self.move_lines.mapped('date_expected') or [False])
        else:
            self.scheduled_date = max(self.move_lines.mapped('date_expected') or [False])

    @api.one
    def _set_scheduled_date(self):
        self.move_lines.write({'date_expected': self.scheduled_date})

    @api.one
    def _has_scrap_move(self):
        # TDE FIXME: better implementation
        self.has_scrap_move = bool(self.env['stock.move'].search_count([('picking_id', '=', self.id), ('scrapped', '=', True)]))

    @api.one
    def _compute_move_line_exist(self):
        self.move_line_exist = bool(self.move_line_ids)

    @api.one
    def _compute_has_packages(self):
        self.has_packages = self.move_line_ids.filtered(lambda ml: ml.result_package_id)

    def _compute_entire_package_ids(self):
        """ This compute method populate the two one2Many containing all entire packages of the picking.
            An entire package is a package that is entirely reserved to be moved from a location to another one.
        """
        for picking in self:
            packages = self.env['stock.quant.package']
            for ml in picking.move_line_ids:
                if ml.package_id.id == ml.result_package_id.id:
                    if picking.state in ('done', 'cancel') or picking._check_move_lines_map_quant_package(ml.package_id):
                        packages |= ml.package_id
            picking.entire_package_ids = packages
            picking.entire_package_detail_ids = packages

    @api.multi
    def _compute_show_check_availability(self):
        for picking in self:
            has_moves_to_reserve = any(
                move.state in ('waiting', 'confirmed', 'partially_available') and
                float_compare(move.product_uom_qty, 0, precision_rounding=move.product_uom.rounding)
                for move in picking.move_lines
            )
            picking.show_check_availability = picking.is_locked and picking.state in ('confirmed', 'waiting', 'assigned') and has_moves_to_reserve

    @api.multi
    @api.depends('state', 'move_lines')
    def _compute_show_mark_as_todo(self):
        for picking in self:
            if not picking.move_lines:
                picking.show_mark_as_todo = False
            elif self._context.get('planned_picking') and picking.state == 'draft':
                picking.show_mark_as_todo = True
            elif picking.state != 'draft' or not picking.id:
                picking.show_mark_as_todo = False
            else:
                picking.show_mark_as_todo = True

    @api.multi
    @api.depends('state', 'is_locked')
    def _compute_show_validate(self):
        for picking in self:
            if self._context.get('planned_picking') and picking.state == 'draft':
                picking.show_validate = False
            elif picking.state not in ('draft', 'confirmed', 'assigned') or not picking.is_locked:
                picking.show_validate = False
            else:
                picking.show_validate = True

    @api.onchange('picking_type_id', 'partner_id')
    def onchange_picking_type(self):
        if self.picking_type_id:
            if self.picking_type_id.default_location_src_id:
                location_id = self.picking_type_id.default_location_src_id.id
            elif self.partner_id:
                location_id = self.partner_id.property_stock_supplier.id
            else:
                customerloc, location_id = self.env['stock.warehouse']._get_partner_locations()

            if self.picking_type_id.default_location_dest_id:
                location_dest_id = self.picking_type_id.default_location_dest_id.id
            elif self.partner_id:
                location_dest_id = self.partner_id.property_stock_customer.id
            else:
                location_dest_id, supplierloc = self.env['stock.warehouse']._get_partner_locations()

            self.location_id = location_id
            self.location_dest_id = location_dest_id
        # TDE CLEANME move into onchange_partner_id
        if self.partner_id:
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

    @api.model
    def create(self, vals):
        # TDE FIXME: clean that brol
        defaults = self.default_get(['name', 'picking_type_id'])
        if vals.get('name', '/') == '/' and defaults.get('name', '/') == '/' and vals.get('picking_type_id', defaults.get('picking_type_id')):
            vals['name'] = self.env['stock.picking.type'].browse(vals.get('picking_type_id', defaults.get('picking_type_id'))).sequence_id.next_by_id()

        # TDE FIXME: what ?
        # As the on_change in one2many list is WIP, we will overwrite the locations on the stock moves here
        # As it is a create the format will be a list of (0, 0, dict)
        if vals.get('move_lines') and vals.get('location_id') and vals.get('location_dest_id'):
            for move in vals['move_lines']:
                if len(move) == 3:
                    move[2]['location_id'] = vals['location_id']
                    move[2]['location_dest_id'] = vals['location_dest_id']
        res = super(Picking, self).create(vals)
        res._autoconfirm_picking()
        return res

    @api.multi
    def write(self, vals):
        res = super(Picking, self).write(vals)
        # Change locations of moves if those of the picking change
        after_vals = {}
        if vals.get('location_id'):
            after_vals['location_id'] = vals['location_id']
        if vals.get('location_dest_id'):
            after_vals['location_dest_id'] = vals['location_dest_id']
        if after_vals:
            self.mapped('move_lines').filtered(lambda move: not move.scrapped).write(after_vals)
        if vals.get('move_lines'):
            self._autoconfirm_picking()
        return res

    @api.multi
    def unlink(self):
        self.mapped('move_lines')._action_cancel()
        self.mapped('move_lines').unlink() # Checks if moves are not done
        return super(Picking, self).unlink()

    # Actions
    # ----------------------------------------

    @api.one
    def action_assign_owner(self):
        self.move_line_ids.write({'owner_id': self.owner_id.id})

    @api.multi
    def do_print_picking(self):
        self.write({'printed': True})
        return self.env.ref('stock.action_report_picking').report_action(self)

    @api.multi
    def action_confirm(self):
        # call `_action_confirm` on every draft move
        self.mapped('move_lines')\
            .filtered(lambda move: move.state == 'draft')\
            ._action_confirm()
        # call `_action_assign` on every confirmed move which location_id bypasses the reservation
        self.filtered(lambda picking: picking.location_id.usage in ('supplier', 'inventory', 'production') and picking.state == 'confirmed')\
            .mapped('move_lines')._action_assign()
        if self.env.context.get('planned_picking') and len(self) == 1:
            action = self.env.ref('stock.action_picking_form')
            result = action.read()[0]
            result['res_id'] = self.id
            result['context'] = {
                'search_default_picking_type_id': [self.picking_type_id.id],
                'default_picking_type_id': self.picking_type_id.id,
                'contact_display': 'partner_address',
                'planned_picking': False,
            }
            return result
        else:
            return True

    @api.multi
    def action_assign(self):
        """ Check availability of picking moves.
        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        @return: True
        """
        self.filtered(lambda picking: picking.state == 'draft').action_confirm()
        moves = self.mapped('move_lines').filtered(lambda move: move.state not in ('draft', 'cancel', 'done'))
        if not moves:
            raise UserError(_('Nothing to check the availability for.'))
        moves._action_assign()
        return True

    @api.multi
    def force_assign(self):
        """ Changes state of picking to available if moves are confirmed or waiting.
        @return: True
        """
        self.mapped('move_lines').filtered(lambda move: move.state in ['confirmed', 'waiting', 'partially_available'])._force_assign()
        return True

    @api.multi
    def action_cancel(self):
        self.mapped('move_lines')._action_cancel()
        self.write({'is_locked': True})
        return True

    @api.multi
    def action_done(self):
        """Changes picking state to done by processing the Stock Moves of the Picking

        Normally that happens when the button "Done" is pressed on a Picking view.
        @return: True
        """
        # TDE FIXME: remove decorator when migration the remaining
        # TDE FIXME: draft -> automatically done, if waiting ?? CLEAR ME
        todo_moves = self.mapped('move_lines').filtered(lambda self: self.state in ['draft', 'partially_available', 'assigned', 'confirmed'])
        # Check if there are ops not linked to moves yet
        for pick in self:
            # # Explode manually added packages
            # for ops in pick.move_line_ids.filtered(lambda x: not x.move_id and not x.product_id):
            #     for quant in ops.package_id.quant_ids: #Or use get_content for multiple levels
            #         self.move_line_ids.create({'product_id': quant.product_id.id,
            #                                    'package_id': quant.package_id.id,
            #                                    'result_package_id': ops.result_package_id,
            #                                    'lot_id': quant.lot_id.id,
            #                                    'owner_id': quant.owner_id.id,
            #                                    'product_uom_id': quant.product_id.uom_id.id,
            #                                    'product_qty': quant.qty,
            #                                    'qty_done': quant.qty,
            #                                    'location_id': quant.location_id.id, # Could be ops too
            #                                    'location_dest_id': ops.location_dest_id.id,
            #                                    'picking_id': pick.id
            #                                    }) # Might change first element
            # # Link existing moves or add moves when no one is related
            for ops in pick.move_line_ids.filtered(lambda x: not x.move_id):
                # Search move with this product
                moves = pick.move_lines.filtered(lambda x: x.product_id == ops.product_id) 
                if moves: #could search move that needs it the most (that has some quantities left)
                    ops.move_id = moves[0].id
                else:
                    new_move = self.env['stock.move'].create({
                                                    'name': _('New Move:') + ops.product_id.display_name,
                                                    'product_id': ops.product_id.id,
                                                    'product_uom_qty': ops.qty_done,
                                                    'product_uom': ops.product_uom_id.id,
                                                    'location_id': pick.location_id.id,
                                                    'location_dest_id': pick.location_dest_id.id,
                                                    'picking_id': pick.id,
                                                   })
                    ops.move_id = new_move.id
                    new_move._action_confirm()
                    todo_moves |= new_move
                    #'qty_done': ops.qty_done})
        todo_moves._action_done()
        self.write({'date_done': fields.Datetime.now()})
        return True

    do_transfer = action_done #TODO:replace later

    def _check_move_lines_map_quant_package(self, package):
        """ This method checks that all product of the package (quant) are well present in the move_line_ids of the picking. """
        all_in = True
        pack_move_lines = self.move_line_ids.filtered(lambda ml: ml.package_id == package)
        keys = ['product_id', 'lot_id']

        grouped_quants = {}
        for k, g in groupby(sorted(package.quant_ids, key=itemgetter(*keys)), key=itemgetter(*keys)):
            grouped_quants[k] = sum(self.env['stock.quant'].concat(*list(g)).mapped('quantity'))

        grouped_ops = {}
        for k, g in groupby(sorted(pack_move_lines, key=itemgetter(*keys)), key=itemgetter(*keys)):
            grouped_ops[k] = sum(self.env['stock.move.line'].concat(*list(g)).mapped('product_qty'))
        if any(grouped_quants.get(key, 0) - grouped_ops.get(key, 0) != 0 for key in grouped_quants) \
                or any(grouped_ops.get(key, 0) - grouped_quants.get(key, 0) != 0 for key in grouped_ops):
            all_in = False
        return all_in

    @api.multi
    def _check_entire_pack(self):
        """ This function check if entire packs are moved in the picking"""
        for picking in self:
            origin_packages = picking.move_line_ids.mapped("package_id")
            for pack in origin_packages:
                if picking._check_move_lines_map_quant_package(pack):
                    picking.move_line_ids.filtered(lambda ml: ml.package_id == pack).write({'result_package_id': pack.id})

    @api.multi
    def do_unreserve(self):
        for picking in self:
            picking.move_lines._do_unreserve()

    @api.multi
    def button_validate(self):
        self.ensure_one()
        if not self.move_lines and not self.move_line_ids:
            raise UserError(_('Please add some lines to move'))

        # If no lots when needed, raise error
        picking_type = self.picking_type_id
        no_quantities_done = all(line.qty_done == 0.0 for line in self.move_line_ids)
        no_initial_demand = all(move.product_uom_qty == 0.0 for move in self.move_lines)
        if no_initial_demand and no_quantities_done:
            raise UserError(_('You cannot validate a transfer if you have not processed any quantity.'))

        if picking_type.use_create_lots or picking_type.use_existing_lots:
            lines_to_check = self.move_line_ids
            if not no_quantities_done:
                lines_to_check = lines_to_check.filtered(
                    lambda line: float_compare(line.qty_done, 0,
                                               precision_rounding=line.product_uom_id.rounding)
                )

            for line in lines_to_check:
                product = line.product_id
                if product and product.tracking != 'none':
                    if not line.lot_name and not line.lot_id:
                        raise UserError(_('You need to supply a lot/serial number for %s.') % product.display_name)
                    elif line.qty_done == 0:
                        raise UserError(_('You cannot validate a transfer if you have not processed any quantity for %s.') % product.display_name)

        if no_quantities_done:
            view = self.env.ref('stock.view_immediate_transfer')
            wiz = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, self.id)]})
            return {
                'name': _('Immediate Transfer?'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.immediate.transfer',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }

        if self._get_overprocessed_stock_moves() and not self._context.get('skip_overprocessed_check'):
            view = self.env.ref('stock.view_overprocessed_transfer')
            wiz = self.env['stock.overprocessed.transfer'].create({'picking_id': self.id})
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.overprocessed.transfer',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }

        # Check backorder should check for other barcodes
        if self._check_backorder():
            return self.action_generate_backorder_wizard()
        self.action_done()
        return

    def action_generate_backorder_wizard(self):
        view = self.env.ref('stock.view_backorder_confirmation')
        wiz = self.env['stock.backorder.confirmation'].create({'pick_ids': [(4, p.id) for p in self]})
        return {
            'name': _('Create Backorder?'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.backorder.confirmation',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': wiz.id,
            'context': self.env.context,
        }

    def action_toggle_is_locked(self):
        self.ensure_one()
        self.is_locked = not self.is_locked
        return True

    def _check_backorder(self):
        """ This method will loop over all the move lines of self and
        check if creating a backorder is necessary. This method is
        called during button_validate if the user has already processed
        some quantities and in the immediate transfer wizard that is
        displayed if the user has not processed any quantities.

        :return: True if a backorder is necessary else False
        """
        quantity_todo = {}
        quantity_done = {}
        for move in self.mapped('move_lines'):
            quantity_todo.setdefault(move.product_id.id, 0)
            quantity_done.setdefault(move.product_id.id, 0)
            quantity_todo[move.product_id.id] += move.product_uom_qty
            quantity_done[move.product_id.id] += move.quantity_done
        for ops in self.mapped('move_line_ids').filtered(lambda x: x.package_id and not x.product_id and not x.move_id):
            for quant in ops.package_id.quant_ids:
                quantity_done.setdefault(quant.product_id.id, 0)
                quantity_done[quant.product_id.id] += quant.qty
        for pack in self.mapped('move_line_ids').filtered(lambda x: x.product_id and not x.move_id):
            quantity_done.setdefault(pack.product_id.id, 0)
            quantity_done[pack.product_id.id] += pack.qty_done
        return any(quantity_done[x] < quantity_todo.get(x, 0) for x in quantity_done)

    @api.multi
    def _autoconfirm_picking(self):
        if not self._context.get('planned_picking'):
            for picking in self.filtered(lambda picking: picking.state not in ('done', 'cancel') and picking.move_lines):
                picking.action_confirm()

    def _get_overprocessed_stock_moves(self):
        self.ensure_one()
        return self.move_lines.filtered(
            lambda move: move.product_uom_qty != 0 and float_compare(move.quantity_done, move.product_uom_qty,
                                                                     precision_rounding=move.product_uom.rounding) == 1
        )

    @api.multi
    def _create_backorder(self, backorder_moves=[]):
        """ Move all non-done lines into a new backorder picking. If the key 'do_only_split' is given in the context, then move all lines not in context.get('split', []) instead of all non-done lines.
        """
        # TDE note: o2o conversion, todo multi
        backorders = self.env['stock.picking']
        for picking in self:
            backorder_moves = backorder_moves or picking.move_lines
            if self._context.get('do_only_split'):
                not_done_bo_moves = backorder_moves.filtered(lambda move: move.id not in self._context.get('split', []))
            else:
                not_done_bo_moves = backorder_moves.filtered(lambda move: move.state not in ('done', 'cancel'))
            if not not_done_bo_moves:
                continue
            backorder_picking = picking.copy({
                'name': '/',
                'move_lines': [],
                'move_line_ids': [],
                'backorder_id': picking.id
            })
            picking.message_post(body=_("Back order <em>%s</em> <b>created</b>.") % (backorder_picking.name))
            not_done_bo_moves.write({'picking_id': backorder_picking.id})
            if not picking.date_done:
                picking.write({'date_done': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
            backorder_picking.action_confirm()
            backorder_picking.action_assign()
            backorders |= backorder_picking
        return backorders

    def _put_in_pack(self):
        package = False
        for pick in self:
            operations = pick.move_line_ids.filtered(lambda o: o.qty_done > 0 and not o.result_package_id)
            operation_ids = self.env['stock.move.line']
            if operations:
                package = self.env['stock.quant.package'].create({})
                for operation in operations:
                    if float_compare(operation.qty_done, operation.product_uom_qty, precision_rounding=operation.product_uom_id.rounding) >= 0:
                        operation_ids |= operation
                    else:
                        quantity_left_todo = float_round(
                            operation.product_uom_qty - operation.qty_done,
                            precision_rounding=operation.product_uom_id.rounding,
                            rounding_method='UP')
                        done_to_keep = operation.qty_done
                        new_operation = operation.copy(
                            default={'product_uom_qty': 0, 'qty_done': operation.qty_done})
                        operation.write({'product_uom_qty': quantity_left_todo, 'qty_done': 0.0})
                        new_operation.write({'product_uom_qty': done_to_keep})
                        operation_ids |= new_operation

                operation_ids.write({'result_package_id': package.id})
            else:
                raise UserError(_('Please process some quantities to put in the pack first!'))
        return package

    def put_in_pack(self):
        return self._put_in_pack()

    def button_scrap(self):
        self.ensure_one()
        products = self.env['product.product']
        for move in self.move_lines:
            if move.state not in ('draft', 'cancel') and move.product_id.type in ('product', 'consu'):
                products |= move.product_id
        return {
            'name': _('Scrap'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.scrap',
            'view_id': self.env.ref('stock.stock_scrap_form_view2').id,
            'type': 'ir.actions.act_window',
            'context': {'default_picking_id': self.id, 'product_ids': products.ids},
            'target': 'new',
        }

    def action_see_move_scrap(self):
        self.ensure_one()
        action = self.env.ref('stock.action_stock_scrap').read()[0]
        scraps = self.env['stock.scrap'].search([('picking_id', '=', self.id)])
        action['domain'] = [('id', 'in', scraps.ids)]
        return action

    def action_see_packages(self):
        self.ensure_one()
        action = self.env.ref('stock.action_package_view').read()[0]
        packages = self.move_line_ids.mapped('result_package_id')
        action['domain'] = [('id', 'in', packages.ids)]
        action['context'] = {'picking_id': self.id}
        return action
