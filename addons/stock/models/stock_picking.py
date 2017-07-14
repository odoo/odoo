# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import namedtuple
import json
import time

from itertools import groupby
from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, pycompat
from odoo.tools.float_utils import float_compare, float_round
from odoo.addons.procurement.models import procurement
from odoo.exceptions import UserError
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
        'Show Operations', default=False)
    show_reserved = fields.Boolean(
        'Show Reserved', default=True)

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

    @api.multi
    def _compute_picking_count(self):
        # TDE TODO count picking can be done using previous two
        domains = {
            'count_picking_draft': [('state', '=', 'draft')],
            'count_picking_waiting': [('state', 'in', ('confirmed', 'waiting'))],
            'count_picking_ready': [('state', 'in', ('assigned', 'partially_available'))],
            'count_picking': [('state', 'in', ('assigned', 'waiting', 'confirmed', 'partially_available'))],
            'count_picking_late': [('min_date', '<', time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)), ('state', 'in', ('assigned', 'waiting', 'confirmed', 'partially_available'))],
            'count_picking_backorders': [('backorder_id', '!=', False), ('state', 'in', ('confirmed', 'assigned', 'waiting', 'partially_available'))],
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

    @api.multi
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

    @api.multi
    def _get_action(self, action_xmlid):
        # TDE TODO check to have one view + custo in methods
        action = self.env.ref(action_xmlid).read()[0]
        if self:
            action['display_name'] = self.display_name
        return action

    @api.multi
    def get_action_picking_tree_late(self):
        return self._get_action('stock.action_picking_tree_late')

    @api.multi
    def get_action_picking_tree_backorder(self):
        return self._get_action('stock.action_picking_tree_backorder')

    @api.multi
    def get_action_picking_tree_waiting(self):
        return self._get_action('stock.action_picking_tree_waiting')

    @api.multi
    def get_action_picking_tree_ready(self):
        return self._get_action('stock.action_picking_tree_ready')

    @api.multi
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
        ('direct', 'Partial'), ('one', 'All at once')], 'Shipping Policy',
        default='direct', required=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="It specifies goods to be deliver partially or all at once")

    state = fields.Selection([
        ('draft', 'Draft'), ('cancel', 'Cancelled'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting Availability'),
        ('partially_available', 'Partially Available'),
        ('assigned', 'Available'), ('done', 'Done')], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, track_visibility='onchange',
        help=" * Draft: not confirmed yet and will not be scheduled until confirmed\n"
             " * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows)\n"
             " * Waiting Availability: still waiting for the availability of products\n"
             " * Partially Available: some products are available and reserved\n"
             " * Ready to Transfer: products reserved, simply waiting for confirmation.\n"
             " * Transferred: has been processed, can't be modified or cancelled anymore\n"
             " * Cancelled: has been cancelled, can't be confirmed anymore")

    group_id = fields.Many2one(
        'procurement.group', 'Procurement Group',
        readonly=True, related='move_lines.group_id', store=True)

    priority = fields.Selection(
        procurement.PROCUREMENT_PRIORITIES, string='Priority',
        compute='_compute_priority', inverse='_set_priority', store=True,
        # default='1', required=True,  # TDE: required, depending on moves ? strange
        index=True, track_visibility='onchange',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="Priority for this picking. Setting manually a value here would set it as priority for all the moves")
    min_date = fields.Datetime(
        'Scheduled Date', compute='_compute_dates', inverse='_set_min_date', store=True,
        index=True, track_visibility='onchange',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="Scheduled time for the first part of the shipment to be processed. Setting manually a value here would set it as expected date for all the stock moves.")
    max_date = fields.Datetime(
        'Max. Expected Date', compute='_compute_dates', store=True,
        index=True,
        help="Scheduled time for the last part of the shipment to be processed")
    date = fields.Datetime(
        'Creation Date',
        default=fields.Datetime.now, index=True, track_visibility='onchange',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="Creation Date, usually the time of the order")
    date_done = fields.Datetime('Date of Transfer', copy=False, readonly=True, help="Completion Date of Transfer")

    location_id = fields.Many2one(
        'stock.location', "Source Location Zone",
        default=lambda self: self.env['stock.picking.type'].browse(self._context.get('default_picking_type_id')).default_location_src_id,
        readonly=True, required=True,
        states={'draft': [('readonly', False)]})
    location_dest_id = fields.Many2one(
        'stock.location', "Destination Location Zone",
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

    move_line_ids = fields.One2many(
        'stock.move.line', 'picking_id', 'Operations',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})

    move_line_exist = fields.Boolean(
        'Has Pack Operations', compute='_compute_move_line_exist',
        help='Check the existence of pack operation on the picking')

    has_packages = fields.Boolean(
        'Has Packages', compute='_compute_has_packages',
        help='Check the existence of destination packages on move lines')

    owner_id = fields.Many2one(
        'res.partner', 'Owner',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="Default Owner")
    printed = fields.Boolean('Printed')
    # Used to search on pickings
    product_id = fields.Many2one('product.product', 'Product', related='move_lines.product_id')
    show_operations = fields.Boolean(related='picking_type_id.show_operations')

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Reference must be unique per company!'),
    ]

    @api.depends('move_type', 'move_lines.state', 'move_lines.picking_id')
    @api.one
    def _compute_state(self):
        ''' State of a picking depends on the state of its related stock.move
         - no moves: draft or assigned (launch_pack_operations)
         - all moves canceled: cancel
         - all moves done (including possible canceled): done
         - All at once picking: least of confirmed / waiting / assigned
         - Partial picking
          - all moves assigned: assigned
          - one of the move is assigned or partially available: partially available
          - otherwise in waiting or confirmed state
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
            # We sort our moves by importance of state:
            #     ------------- 0
            #     | Confirmed |
            #     -------------
            #     |  Partial  |
            #     -------------
            #     |  Waiting  |
            #     -------------
            #     |  Assigned |
            #     ------------- len - 1
            sort_map = {
                'assigned': 4,
                'waiting': 3,
                'partially_available': 2,
                'confirmed': 1,
            }
            moves_todo = self.move_lines\
                .filtered(lambda move: move.state not in ['cancel', 'done'])\
                .sorted(key=lambda move: sort_map.get(move.state, 0))
            if self.move_type == 'one':
                if moves_todo[0].state in ('partially_available', 'confirmed'):
                    self.state = 'confirmed'
                else:
                    self.state = moves_todo[0].state or 'draft'
            elif moves_todo[0].state != 'assigned' and any(x.state in ['assigned', 'partially_available'] for x in moves_todo):
                self.state = 'partially_available'
            else:
                # take the less important state among all move_lines.
                self.state = moves_todo[-1].state or 'draft'

    @api.one
    @api.depends('move_lines.priority')
    def _compute_priority(self):
        self.priority = self.mapped('move_lines') and max(self.mapped('move_lines').mapped('priority')) or '1'

    @api.one
    def _set_priority(self):
        self.move_lines.write({'priority': self.priority})

    @api.one
    @api.depends('move_lines.date_expected')
    def _compute_dates(self):
        self.min_date = min(self.move_lines.mapped('date_expected') or [False])
        self.max_date = max(self.move_lines.mapped('date_expected') or [False])

    @api.one
    def _set_min_date(self):
        self.move_lines.write({'date_expected': self.min_date})

    @api.one
    def _has_scrap_move(self):
        # TDE FIXME: better implementation
        self.has_scrap_move = bool(self.env['stock.move'].search_count([('picking_id', '=', self.id), ('scrapped', '=', True)]))

    @api.one
    def _compute_move_line_exist(self):
        self.move_line_exist = bool(self.move_line_ids)

    @api.one
    def _compute_has_packages(self):
        has_packages = False
        for pack_op in self.move_line_ids:
            if pack_op.result_package_id:
                has_packages = True
                break
        self.has_packages = has_packages

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
        return super(Picking, self).create(vals)

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
        return res

    @api.multi
    def unlink(self):
        self.mapped('move_lines').action_cancel()
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
        # call `action_confirm` on every draft move
        self.mapped('move_lines')\
            .filtered(lambda move: move.state == 'draft')\
            .action_confirm()
        # call `action_assign` on every confirmed move which location_id bypasses the reservation
        self.filtered(lambda picking: picking.location_id.usage in ('supplier', 'inventory', 'production'))\
            .filtered(lambda move: move.state == 'confirmed')\
            .mapped('move_lines').action_assign()
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
        moves.action_assign()
        self._check_entire_pack()
        return True

    @api.multi
    def force_assign(self):
        """ Changes state of picking to available if moves are confirmed or waiting.
        @return: True
        """
        self.mapped('move_lines').filtered(lambda move: move.state in ['confirmed', 'waiting', 'partially_available']).force_assign()
        return True

    @api.multi
    def action_cancel(self):
        self.mapped('move_lines').action_cancel()
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
                    new_move.action_confirm()
                    todo_moves |= new_move
                    #'qty_done': ops.qty_done})
        todo_moves.action_done()
        return True

    do_transfer = action_done #TODO:replace later

    @api.multi
    def _check_entire_pack(self):
        """ This function check if entire packs are moved in the picking"""
        for picking in self:
            origin_packages = picking.move_line_ids.mapped("package_id")
            for pack in origin_packages:
                all_in = True
                packops = picking.move_line_ids.filtered(lambda x: x.package_id == pack)
                keys = ['product_id', 'lot_id']

                grouped_quants = {}
                for k, g in groupby(sorted(pack.quant_ids, key=itemgetter(*keys)), key=itemgetter(*keys)):
                    grouped_quants[k] = sum(self.env['stock.quant'].concat(*list(g)).mapped('quantity'))

                grouped_ops = {}
                for k, g in groupby(sorted(packops, key=itemgetter(*keys)), key=itemgetter(*keys)):
                    grouped_ops[k] = sum(self.env['stock.move.line'].concat(*list(g)).mapped('product_qty'))
                if any(grouped_quants[key] - grouped_ops.get(key, 0) != 0 for key in grouped_quants)\
                        or any(grouped_ops[key] - grouped_quants[key] != 0 for key in grouped_ops):
                    all_in = False
                if all_in and packops:
                    packops.write({'result_package_id': pack.id})

    @api.multi
    def do_unreserve(self):
        for move in self:
            for move_line in move.move_lines:
                move_line.do_unreserve()
        self.write({'state': 'confirmed'})

    @api.multi
    def button_validate(self):
        self.ensure_one()
        move_line_delete = self.env['stock.move.line']
        if not self.move_lines and not self.move_line_ids:
            raise UserError(_('Please add some lines to move'))
        # In draft or with no pack operations edited yet, ask if we can just do everything
        if self.state == 'draft' or all([x.qty_done == 0.0 for x in self.move_line_ids]):
            # If no lots when needed, raise error
            picking_type = self.picking_type_id
            if (picking_type.use_create_lots or picking_type.use_existing_lots):
                for pack in self.move_line_ids:
                    if pack.product_id and pack.product_id.tracking != 'none':
                        raise UserError(_('Some products require lots/serial numbers, so you need to specify those first!'))
            view = self.env.ref('stock.view_immediate_transfer')
            wiz = self.env['stock.immediate.transfer'].create({'pick_id': self.id})
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

        # Check backorder should check for other barcodes
        if self.check_backorder():
            view = self.env.ref('stock.view_backorder_confirmation')
            wiz = self.env['stock.backorder.confirmation'].create({'pick_id': self.id})
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
        for operation in self.move_line_ids:
            if operation.qty_done < 0:
                raise UserError(_('No negative quantities allowed'))
            if operation.qty_done > 0:
                pass
                #operation.write({'product_qty': operation.qty_done})
            else:
                move_line_delete |= operation
        if move_line_delete:
            move_line_delete.unlink()
        self.action_done()
        return

    do_new_transfer = button_validate #TODO: replace later

    def check_backorder(self):
        self.ensure_one()
        quantity_todo = {}
        quantity_done = {}
        for move in self.move_lines:
            quantity_todo.setdefault(move.product_id.id, 0)
            quantity_done.setdefault(move.product_id.id, 0)
            quantity_todo[move.product_id.id] += move.product_qty
            quantity_done[move.product_id.id] += move.quantity_done #TODO: convert to base units
        for ops in self.move_line_ids.filtered(lambda x: x.package_id and not x.product_id and not x.move_id):
            for quant in ops.package_id.quant_ids:
                quantity_done.setdefault(quant.product_id.id, 0)
                quantity_done[quant.product_id.id] += quant.qty
        for pack in self.move_line_ids.filtered(lambda x: x.product_id and not x.move_id):
            quantity_done.setdefault(pack.product_id.id, 0)
            quantity_done[pack.product_id.id] += pack.qty_done
        return any(quantity_done[x] < quantity_todo.get(x, 0) for x in quantity_done)

    def _create_extra_moves(self):
        '''This function creates move lines on a picking, at the time of do_transfer, based on
        unexpected product transfers (or exceeding quantities) found in the pack operations.
        '''
        # TDE FIXME: move to batch
        self.ensure_one()
        moves = self.env['stock.move']
        for move_line in self.move_line_ids:
            for product, remaining_qty in pycompat.items(move_line._get_remaining_prod_quantities()):
                if float_compare(remaining_qty, 0, precision_rounding=product.uom_id.rounding) > 0:
                    vals = self._prepare_values_extra_move(move_line, product, remaining_qty)
                    moves |= moves.create(vals)
        if moves:
            moves.with_context(skip_check=True).action_confirm()
        return moves

    @api.model
    def _prepare_values_extra_move(self, op, product, remaining_qty):
        """
        Creates an extra move when there is no corresponding original move to be copied
        """
        Uom = self.env["product.uom"]
        uom_id = product.uom_id.id
        qty = remaining_qty
        if op.product_id and op.product_uom_id and op.product_uom_id.id != product.uom_id.id:
            if op.product_uom_id.factor > product.uom_id.factor:  # If the pack operation's is a smaller unit
                uom_id = op.product_uom_id.id
                # HALF-UP rounding as only rounding errors will be because of propagation of error from default UoM
                qty = product.uom_id._compute_quantity(remaining_qty, op.product_uom_id, rounding_method='HALF-UP')
        picking = op.picking_id
        ref = product.default_code
        name = '[' + ref + ']' + ' ' + product.name if ref else product.name
        proc_id = False
        for m in op.linked_move_operation_ids:
            if m.move_id.procurement_id:
                proc_id = m.move_id.procurement_id.id
                break
        return {
            'picking_id': picking.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'product_id': product.id,
            'procurement_id': proc_id,
            'product_uom': uom_id,
            'product_uom_qty': qty,
            'name': _('Extra Move: ') + name,
            'state': 'draft',
            'restrict_partner_id': op.owner_id.id,
            'group_id': picking.group_id.id,
        }

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

    @api.multi
    def _put_in_pack(self):
        package = False
        for pick in self:
            operations = pick.move_line_ids.filtered(lambda o: o.qty_done > 0 and not o.result_package_id)
            operation_ids = self.env['stock.move.line']
            if operations:
                package = self.env['stock.quant.package'].create({})
                for operation in operations:
                    if float_compare(operation.qty_done, operation.product_qty, precision_rounding=operation.product_uom_id.rounding) >= 0:
                        operation_ids |= operation
                    else:
                        quantity_left_todo = float_round(
                            operation.product_qty - operation.qty_done,
                            precision_rounding=operation.product_uom_id.rounding,
                            rounding_method='UP')
                        new_operation = operation.copy(
                            default={'product_uom_qty': operation.qty_done, 'qty_done': operation.qty_done})
                        operation.write({'product_uom_qty': quantity_left_todo, 'qty_done': 0.0})
                        operation_ids |= new_operation

                operation_ids.write({'result_package_id': package.id})
            else:
                raise UserError(_('Please process some quantities to put in the pack first!'))
        return package

    @api.multi
    def put_in_pack(self):
        return self._put_in_pack()

    @api.multi
    def button_scrap(self):
        self.ensure_one()
        # only stockable products are scrapeable
        scrapeable_products = self.move_line_ids.mapped('product_id').filtered(lambda p: p.type == 'product')
        return {
            'name': _('Scrap'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.scrap',
            'view_id': self.env.ref('stock.stock_scrap_form_view2').id,
            'type': 'ir.actions.act_window',
            'context': {'default_picking_id': self.id, 'product_ids': scrapeable_products.ids},
            'target': 'new',
        }

    @api.multi
    def action_see_move_scrap(self):
        self.ensure_one()
        action = self.env.ref('stock.action_stock_scrap').read()[0]
        scraps = self.env['stock.scrap'].search([('picking_id', '=', self.id)])
        action['domain'] = [('id', 'in', scraps.ids)]
        return action

    @api.multi
    def action_see_packages(self):
        self.ensure_one()
        action = self.env.ref('stock.action_package_view').read()[0]
        packages = self.move_line_ids.mapped('result_package_id')
        action['domain'] = [('id', 'in', packages.ids)]
        action['context'] = {'picking_id': self.id}
        return action
