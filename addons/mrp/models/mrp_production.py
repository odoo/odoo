# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import datetime
import math
import re

from ast import literal_eval
from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_round, float_is_zero, format_datetime
from odoo.tools.misc import OrderedSet, format_date, groupby as tools_groupby

from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES

SIZE_BACK_ORDER_NUMERING = 3


class MrpProduction(models.Model):
    """ Manufacturing Orders """
    _name = 'mrp.production'
    _description = 'Production Order'
    _date_name = 'date_planned_start'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, date_planned_start asc,id'

    @api.model
    def _get_default_date_planned_start(self):
        if self.env.context.get('default_date_deadline'):
            return fields.Datetime.to_datetime(self.env.context.get('default_date_deadline'))
        return datetime.datetime.now()

    @api.model
    def _get_default_is_locked(self):
        return not self.user_has_groups('mrp.group_unlocked_by_default')

    name = fields.Char('Reference', copy=False, readonly=True)
    priority = fields.Selection(
        PROCUREMENT_PRIORITIES, string='Priority', default='0',
        help="Components will be reserved first for the MO with the highest priorities.")
    backorder_sequence = fields.Integer("Backorder Sequence", default=0, copy=False, help="Backorder sequence, if equals to 0 means there is not related backorder")
    origin = fields.Char(
        'Source', copy=False,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="Reference of the document that generated this production order request.")

    product_id = fields.Many2one(
        'product.product', 'Product',
        domain="""[
            ('type', 'in', ['product', 'consu']),
            '|',
                ('company_id', '=', False),
                ('company_id', '=', company_id)
        ]
        """,
        compute='_compute_product_id', store=True, copy=True, precompute=True,
        readonly=True, required=True, check_company=True,
        states={'draft': [('readonly', False)]})
    product_variant_attributes = fields.Many2many('product.template.attribute.value', related='product_id.product_template_attribute_value_ids')
    product_tracking = fields.Selection(related='product_id.tracking')
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', related='product_id.product_tmpl_id')
    product_qty = fields.Float(
        'Quantity To Produce', digits='Product Unit of Measure',
        readonly=False, required=True, tracking=True, default=1.0,
        compute='_compute_product_qty', store=True, copy=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        readonly=False, required=True, compute='_compute_uom_id', store=True, copy=True, precompute=True,
        domain="[('category_id', '=', product_uom_category_id)]")
    lot_producing_id = fields.Many2one(
        'stock.lot', string='Lot/Serial Number', copy=False,
        domain="[('product_id', '=', product_id), ('company_id', '=', company_id)]", check_company=True)
    qty_producing = fields.Float(string="Quantity Producing", digits='Product Unit of Measure', copy=False)
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    product_uom_qty = fields.Float(string='Total Quantity', compute='_compute_product_uom_qty', store=True)
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type', copy=True, readonly=False,
        compute='_compute_picking_type_id', store=True, precompute=True,
        domain="[('code', '=', 'mrp_operation'), ('company_id', '=', company_id)]",
        required=True, check_company=True, index=True)
    use_create_components_lots = fields.Boolean(related='picking_type_id.use_create_components_lots')
    use_auto_consume_components_lots = fields.Boolean(related='picking_type_id.use_auto_consume_components_lots')
    location_src_id = fields.Many2one(
        'stock.location', 'Components Location',
        compute='_compute_locations', store=True, check_company=True,
        readonly=False, required=True, precompute=True,
        domain="[('usage','=','internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Location where the system will look for components.")
    # this field was added to be passed a default in view for manual raw moves
    warehouse_id = fields.Many2one(related='location_src_id.warehouse_id')
    location_dest_id = fields.Many2one(
        'stock.location', 'Finished Products Location',
        compute='_compute_locations', store=True, check_company=True,
        readonly=False, required=True, precompute=True,
        domain="[('usage','=','internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Location where the system will stock the finished products.")
    date_planned_start = fields.Datetime(
        'Scheduled Date', copy=False, default=_get_default_date_planned_start,
        help="Date at which you plan to start the production.",
        index=True, required=True)
    date_planned_finished = fields.Datetime(
        'Scheduled End Date',
        compute='_compute_date_planned_finished', store=True,
        help="Date at which you plan to finish the production.",
        copy=False)
    date_deadline = fields.Datetime(
        'Deadline', copy=False, store=True, readonly=True, compute='_compute_date_deadline',
        help="Informative date allowing to define when the manufacturing order should be processed at the latest to fulfill delivery on time.")
    date_start = fields.Datetime('Start Date', copy=False, readonly=True)
    date_finished = fields.Datetime('End Date', copy=False, readonly=True)

    production_duration_expected = fields.Float("Expected Duration", help="Total expected duration (in minutes)", compute='_compute_production_duration_expected')
    production_real_duration = fields.Float("Real Duration", help="Total real duration (in minutes)", compute='_compute_production_real_duration')

    bom_id = fields.Many2one(
        'mrp.bom', 'Bill of Material', readonly=False,
        domain="""[
        '&',
            '|',
                ('company_id', '=', False),
                ('company_id', '=', company_id),
            '&',
                '|',
                    ('product_id','=',product_id),
                    '&',
                        ('product_tmpl_id.product_variant_ids','=',product_id),
                        ('product_id','=',False),
        ('type', '=', 'normal')]""",
        check_company=True, compute='_compute_bom_id', store=True, precompute=True,
        help="Bill of Materials allow you to define the list of required components to make a finished product.")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('progress', 'In Progress'),
        ('to_close', 'To Close'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], string='State',
        compute='_compute_state', copy=False, index=True, readonly=True,
        store=True, tracking=True,
        help=" * Draft: The MO is not confirmed yet.\n"
             " * Confirmed: The MO is confirmed, the stock rules and the reordering of the components are trigerred.\n"
             " * In Progress: The production has started (on the MO or on the WO).\n"
             " * To Close: The production is done, the MO has to be closed.\n"
             " * Done: The MO is closed, the stock moves are posted. \n"
             " * Cancelled: The MO has been cancelled, can't be confirmed anymore.")
    reservation_state = fields.Selection([
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('waiting', 'Waiting Another Operation')],
        string='MO Readiness',
        compute='_compute_reservation_state', copy=False, index=True, readonly=True,
        store=True, tracking=True,
        help="Manufacturing readiness for this MO, as per bill of material configuration:\n\
            * Ready: The material is available to start the production.\n\
            * Waiting: The material is not available to start the production.\n")

    move_raw_ids = fields.One2many(
        'stock.move', 'raw_material_production_id', 'Components',
        compute='_compute_move_raw_ids', store=True, readonly=False,
        copy=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        domain=[('scrapped', '=', False)])
    move_finished_ids = fields.One2many(
        'stock.move', 'production_id', 'Finished Products', readonly=False,
        compute='_compute_move_finished_ids', store=True, copy=False,
        domain=[('scrapped', '=', False)])
    move_byproduct_ids = fields.One2many('stock.move', compute='_compute_move_byproduct_ids', inverse='_set_move_byproduct_ids')
    finished_move_line_ids = fields.One2many(
        'stock.move.line', compute='_compute_lines', inverse='_inverse_lines', string="Finished Product"
        )
    workorder_ids = fields.One2many(
        'mrp.workorder', 'production_id', 'Work Orders', copy=True,
        compute='_compute_workorder_ids', store=True, readonly=False)
    move_dest_ids = fields.One2many('stock.move', 'created_production_id',
        string="Stock Movements of Produced Goods")

    unreserve_visible = fields.Boolean(
        'Allowed to Unreserve Production', compute='_compute_unreserve_visible',
        help='Technical field to check when we can unreserve')
    reserve_visible = fields.Boolean(
        'Allowed to Reserve Production', compute='_compute_unreserve_visible',
        help='Technical field to check when we can reserve quantities')
    user_id = fields.Many2one(
        'res.users', 'Responsible', default=lambda self: self.env.user,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        domain=lambda self: [('groups_id', 'in', self.env.ref('mrp.group_mrp_user').id)])
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company,
        index=True, required=True)

    qty_produced = fields.Float(compute="_get_produced_qty", string="Quantity Produced")
    procurement_group_id = fields.Many2one(
        'procurement.group', 'Procurement Group',
        copy=False)
    product_description_variants = fields.Char('Custom Description')
    orderpoint_id = fields.Many2one('stock.warehouse.orderpoint', 'Orderpoint', copy=False, index='btree_not_null')
    propagate_cancel = fields.Boolean(
        'Propagate cancel and split',
        help='If checked, when the previous move of the move (which was generated by a next procurement) is cancelled or split, the move generated by this move will too')
    delay_alert_date = fields.Datetime('Delay Alert Date', compute='_compute_delay_alert_date', search='_search_delay_alert_date')
    json_popover = fields.Char('JSON data for the popover widget', compute='_compute_json_popover')
    scrap_ids = fields.One2many('stock.scrap', 'production_id', 'Scraps')
    scrap_count = fields.Integer(compute='_compute_scrap_move_count', string='Scrap Move')
    unbuild_ids = fields.One2many('mrp.unbuild', 'mo_id', 'Unbuilds')
    unbuild_count = fields.Integer(compute='_compute_unbuild_count', string='Number of Unbuilds')
    is_locked = fields.Boolean('Is Locked', default=_get_default_is_locked, copy=False)
    is_planned = fields.Boolean('Its Operations are Planned', compute="_compute_is_planned", store=True)

    show_final_lots = fields.Boolean('Show Final Lots', compute='_compute_show_lots')
    production_location_id = fields.Many2one('stock.location', "Production Location", compute="_compute_production_location", store=True)
    picking_ids = fields.Many2many('stock.picking', compute='_compute_picking_ids', string='Picking associated to this manufacturing order')
    delivery_count = fields.Integer(string='Delivery Orders', compute='_compute_picking_ids')
    confirm_cancel = fields.Boolean(compute='_compute_confirm_cancel')
    consumption = fields.Selection([
        ('flexible', 'Allowed'),
        ('warning', 'Allowed with warning'),
        ('strict', 'Blocked')],
        required=True,
        readonly=True,
        default='flexible',
    )

    mrp_production_child_count = fields.Integer("Number of generated MO", compute='_compute_mrp_production_child_count')
    mrp_production_source_count = fields.Integer("Number of source MO", compute='_compute_mrp_production_source_count')
    mrp_production_backorder_count = fields.Integer("Count of linked backorder", compute='_compute_mrp_production_backorder')
    show_lock = fields.Boolean('Show Lock/unlock buttons', compute='_compute_show_lock')
    components_availability = fields.Char(
        string="Component Status", compute='_compute_components_availability',
        help="Latest component availability status for this MO. If green, then the MO's readiness status is ready, as per BOM configuration.")
    components_availability_state = fields.Selection([
        ('available', 'Available'),
        ('expected', 'Expected'),
        ('late', 'Late')], compute='_compute_components_availability')
    production_capacity = fields.Float(compute='_compute_production_capacity', help="Quantity that can be produced with the current stock of components")
    show_lot_ids = fields.Boolean('Display the serial number shortcut on the moves', compute='_compute_show_lot_ids')
    forecasted_issue = fields.Boolean(compute='_compute_forecasted_issue')
    show_serial_mass_produce = fields.Boolean('Display the serial mass produce wizard action', compute='_compute_show_serial_mass_produce')
    show_allocation = fields.Boolean(
        compute='_compute_show_allocation',
        help='Technical Field used to decide whether the button "Allocation" should be displayed.')
    allow_workorder_dependencies = fields.Boolean('Allow Work Order Dependencies')

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Reference must be unique per Company!'),
        ('qty_positive', 'check (product_qty > 0)', 'The quantity to produce must be positive!'),
    ]

    @api.depends('procurement_group_id.stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids',
                 'procurement_group_id.stock_move_ids.move_orig_ids.created_production_id.procurement_group_id.mrp_production_ids')
    def _compute_mrp_production_child_count(self):
        for production in self:
            production.mrp_production_child_count = len(production._get_children())

    @api.depends('procurement_group_id.mrp_production_ids.move_dest_ids.group_id.mrp_production_ids',
                 'procurement_group_id.stock_move_ids.move_dest_ids.group_id.mrp_production_ids')
    def _compute_mrp_production_source_count(self):
        for production in self:
            production.mrp_production_source_count = len(production._get_sources())

    @api.depends('procurement_group_id.mrp_production_ids')
    def _compute_mrp_production_backorder(self):
        for production in self:
            production.mrp_production_backorder_count = len(production.procurement_group_id.mrp_production_ids)

    @api.depends('company_id')
    def _compute_picking_type_id(self):
        domain = [
            ('code', '=', 'mrp_operation'),
            ('warehouse_id.company_id', 'in', self.company_id.ids),
        ]
        picking_types = self.env['stock.picking.type'].search_read(domain, ['company_id'], load=False, limit=1)
        picking_type_by_company = {pt['company_id']: pt['id'] for pt in picking_types}
        for mo in self:
            if mo.picking_type_id and mo.picking_type_id.company_id == mo.company_id:
                continue
            mo.picking_type_id = picking_type_by_company.get(mo.company_id.id, False)

    @api.depends('bom_id', 'product_id')
    def _compute_uom_id(self):
        for production in self:
            if production.state != 'draft':
                continue
            if production.bom_id and production._origin.bom_id != production.bom_id:
                production.product_uom_id = production.bom_id.product_uom_id
            elif production.product_id:
                production.product_uom_id = production.product_id.uom_id
            else:
                production.product_uom_id = False

    @api.depends('picking_type_id')
    def _compute_locations(self):
        for production in self:
            if not production.picking_type_id.default_location_src_id or not production.picking_type_id.default_location_dest_id:
                company_id = production.company_id.id if (production.company_id and production.company_id in self.env.companies) else self.env.company.id
                fallback_loc = self.env['stock.warehouse'].search([('company_id', '=', company_id)], limit=1).lot_stock_id
            production.location_src_id = production.picking_type_id.default_location_src_id.id or fallback_loc.id
            production.location_dest_id = production.picking_type_id.default_location_dest_id.id or fallback_loc.id

    @api.depends('state', 'reservation_state', 'date_planned_start', 'move_raw_ids', 'move_raw_ids.forecast_availability', 'move_raw_ids.forecast_expected_date')
    def _compute_components_availability(self):
        productions = self.filtered(lambda mo: mo.state not in ('cancel', 'done', 'draft'))
        productions.components_availability_state = 'available'
        productions.components_availability = _('Available')

        other_productions = self - productions
        other_productions.components_availability = False
        other_productions.components_availability_state = False

        all_raw_moves = productions.move_raw_ids
        # Force to prefetch more than 1000 by 1000
        all_raw_moves._fields['forecast_availability'].compute_value(all_raw_moves)
        for production in productions:
            if any(float_compare(move.forecast_availability, 0 if move.state == 'draft' else move.product_qty, precision_rounding=move.product_id.uom_id.rounding) == -1 for move in production.move_raw_ids):
                production.components_availability = _('Not Available')
                production.components_availability_state = 'late'
            else:
                forecast_date = max(production.move_raw_ids.filtered('forecast_expected_date').mapped('forecast_expected_date'), default=False)
                if forecast_date:
                    production.components_availability = _('Exp %s', format_date(self.env, forecast_date))
                    if production.date_planned_start:
                        production.components_availability_state = 'late' if forecast_date > production.date_planned_start else 'expected'

    @api.depends('bom_id')
    def _compute_product_id(self):
        for production in self:
            bom = production.bom_id
            if bom and (
                not production.product_id or bom.product_tmpl_id != production.product_tmpl_id
                or bom.product_id and bom.product_id != production.product_id
            ):
                production.product_id = bom.product_id or bom.product_tmpl_id.product_variant_id

    @api.depends('product_id', 'picking_type_id')
    def _compute_bom_id(self):
        mo_by_picking_type_and_company_id = defaultdict(lambda: self.env['mrp.production'])
        for mo in self:
            if not mo.product_id and not mo.bom_id:
                mo.bom_id = False
                continue
            mo_by_picking_type_and_company_id[(mo.picking_type_id, mo.company_id.id)] |= mo

        for (picking_type, company_id), productions in mo_by_picking_type_and_company_id.items():
            boms_by_product = self.env['mrp.bom'].with_context(active_test=True)._bom_find(productions.product_id, picking_type=picking_type, company_id=company_id, bom_type='normal')
            for production in productions:
                if not production.bom_id or production.bom_id.product_tmpl_id != production.product_tmpl_id or (production.bom_id.product_id and production.bom_id.product_id != production.product_id):
                    bom = boms_by_product[production.product_id]
                    production.bom_id = bom.id or False

    @api.depends('bom_id')
    def _compute_product_qty(self):
        for production in self:
            if production.state != 'draft':
                continue
            if production.bom_id and production._origin.bom_id != production.bom_id:
                production.product_qty = production.bom_id.product_qty

    @api.depends('move_raw_ids')
    def _compute_production_capacity(self):
        for production in self:
            production.production_capacity = production.product_qty
            moves = production.move_raw_ids.filtered(lambda move: move.unit_factor and move.product_id.type != 'consu')
            if moves:
                production_capacity = min(moves.mapped(lambda move: move.product_id.uom_id._compute_quantity(move.product_id.qty_available, move.product_uom) / move.unit_factor))
                production.production_capacity = min(production.product_qty, float_round(production_capacity, precision_rounding=production.product_id.uom_id.rounding))

    @api.depends('move_finished_ids.date_deadline')
    def _compute_date_deadline(self):
        for production in self:
            production.date_deadline = min(production.move_finished_ids.filtered('date_deadline').mapped('date_deadline'), default=production.date_deadline or False)

    @api.depends('workorder_ids.duration_expected')
    def _compute_production_duration_expected(self):
        for production in self:
            production.production_duration_expected = sum(production.workorder_ids.mapped('duration_expected'))

    @api.depends('workorder_ids.duration')
    def _compute_production_real_duration(self):
        for production in self:
            production.production_real_duration = sum(production.workorder_ids.mapped('duration'))

    @api.depends("workorder_ids.date_planned_start", "workorder_ids.date_planned_finished")
    def _compute_is_planned(self):
        for production in self:
            if production.workorder_ids:
                production.is_planned = any(wo.date_planned_start and wo.date_planned_finished for wo in production.workorder_ids)
            else:
                production.is_planned = False

    @api.depends('move_raw_ids.delay_alert_date')
    def _compute_delay_alert_date(self):
        delay_alert_date_data = self.env['stock.move']._read_group([('id', 'in', self.move_raw_ids.ids), ('delay_alert_date', '!=', False)], ['delay_alert_date:max'], 'raw_material_production_id')
        delay_alert_date_data = {data['raw_material_production_id'][0]: data['delay_alert_date'] for data in delay_alert_date_data}
        for production in self:
            production.delay_alert_date = delay_alert_date_data.get(production.id, False)

    def _compute_json_popover(self):
        production_no_alert = self.filtered(lambda m: m.state in ('done', 'cancel') or not m.delay_alert_date)
        production_no_alert.json_popover = False
        for production in (self - production_no_alert):
            production.json_popover = json.dumps({
                'delay_alert_date': format_datetime(self.env, production.delay_alert_date, dt_format=False),
                'late_elements': [{
                    'id': late_document.id,
                    'name': late_document.display_name,
                    'model': late_document._name,
                } for late_document in production.move_raw_ids.filtered(lambda m: m.delay_alert_date).move_orig_ids._delay_alert_get_documents()
                ]
            })

    @api.depends('move_raw_ids.state', 'move_finished_ids.state')
    def _compute_confirm_cancel(self):
        """ If the manufacturing order contains some done move (via an intermediate
        post inventory), the user has to confirm the cancellation.
        """
        domain = [
            ('state', '=', 'done'),
            '|',
                ('production_id', 'in', self.ids),
                ('raw_material_production_id', 'in', self.ids)
        ]
        res = self.env['stock.move'].read_group(domain, ['state', 'production_id', 'raw_material_production_id'], ['production_id', 'raw_material_production_id'], lazy=False)
        productions_with_done_move = {}
        for rec in res:
            production_record = rec['production_id'] or rec['raw_material_production_id']
            if production_record:
                productions_with_done_move[production_record[0]] = True
        for production in self:
            production.confirm_cancel = productions_with_done_move.get(production.id, False)

    @api.depends('procurement_group_id', 'procurement_group_id.stock_move_ids.group_id')
    def _compute_picking_ids(self):
        for order in self:
            order.picking_ids = self.env['stock.picking'].search([
                ('group_id', '=', order.procurement_group_id.id), ('group_id', '!=', False),
            ])
            order.delivery_count = len(order.picking_ids)

    @api.depends('product_uom_id', 'product_qty', 'product_id.uom_id')
    def _compute_product_uom_qty(self):
        for production in self:
            if production.product_id.uom_id != production.product_uom_id:
                production.product_uom_qty = production.product_uom_id._compute_quantity(production.product_qty, production.product_id.uom_id)
            else:
                production.product_uom_qty = production.product_qty

    @api.depends('product_id', 'company_id')
    def _compute_production_location(self):
        if not self.company_id:
            return
        location_by_company = self.env['stock.location']._read_group([
            ('company_id', 'in', self.company_id.ids),
            ('usage', '=', 'production')
        ], ['company_id', 'ids:array_agg(id)'], ['company_id'])
        location_by_company = {lbc['company_id'][0]: lbc['ids'] for lbc in location_by_company}
        for production in self:
            if production.product_id:
                production.production_location_id = production.product_id.with_company(production.company_id).property_stock_production
            else:
                production.production_location_id = location_by_company.get(production.company_id.id)[0]

    @api.depends('product_id.tracking')
    def _compute_show_lots(self):
        for production in self:
            production.show_final_lots = production.product_id.tracking != 'none'

    def _inverse_lines(self):
        """ Little hack to make sure that when you change something on these objects, it gets saved"""
        pass

    @api.depends('move_finished_ids.move_line_ids')
    def _compute_lines(self):
        for production in self:
            production.finished_move_line_ids = production.move_finished_ids.mapped('move_line_ids')

    @api.depends(
        'move_raw_ids.state', 'move_raw_ids.quantity_done', 'move_finished_ids.state',
        'workorder_ids.state', 'product_qty', 'qty_producing')
    def _compute_state(self):
        """ Compute the production state. This uses a similar process to stock
        picking, but has been adapted to support having no moves. This adaption
        includes some state changes outside of this compute.

        There exist 3 extra steps for production:
        - progress: At least one item is produced or consumed.
        - to_close: The quantity produced is greater than the quantity to
        produce and all work orders has been finished.
        """
        for production in self:
            if not production.state or not production.product_uom_id:
                production.state = 'draft'
            elif production.state == 'cancel' or (production.move_finished_ids and all(move.state == 'cancel' for move in production.move_finished_ids)):
                production.state = 'cancel'
            elif (
                production.state == 'done'
                or (production.move_raw_ids and all(move.state in ('cancel', 'done') for move in production.move_raw_ids))
                and all(move.state in ('cancel', 'done') for move in production.move_finished_ids)
            ):
                production.state = 'done'
            elif production.workorder_ids and all(wo_state in ('done', 'cancel') for wo_state in production.workorder_ids.mapped('state')):
                production.state = 'to_close'
            elif not production.workorder_ids and float_compare(production.qty_producing, production.product_qty, precision_rounding=production.product_uom_id.rounding) >= 0:
                production.state = 'to_close'
            elif any(wo_state in ('progress', 'done') for wo_state in production.workorder_ids.mapped('state')):
                production.state = 'progress'
            elif production.product_uom_id and not float_is_zero(production.qty_producing, precision_rounding=production.product_uom_id.rounding):
                production.state = 'progress'
            elif any(not float_is_zero(move.quantity_done, precision_rounding=move.product_uom.rounding or move.product_id.uom_id.rounding) for move in production.move_raw_ids):
                production.state = 'progress'

    @api.depends('bom_id', 'product_id', 'product_qty', 'product_uom_id')
    def _compute_workorder_ids(self):
        for production in self:
            if production.state != 'draft':
                continue
            workorders_list = [Command.link(wo.id) for wo in production.workorder_ids.filtered(lambda wo: not wo.operation_id)]
            if not production.bom_id and not production._origin.product_id:
                production.workorder_ids = workorders_list
            if production.product_id != production._origin.product_id:
                production.workorder_ids = [Command.clear()]
            if production.bom_id and production.product_id and production.product_qty > 0:
                # keep manual entries
                workorders_values = []
                product_qty = production.product_uom_id._compute_quantity(production.product_qty, production.bom_id.product_uom_id)
                exploded_boms, dummy = production.bom_id.explode(production.product_id, product_qty / production.bom_id.product_qty, picking_type=production.bom_id.picking_type_id)

                for bom, bom_data in exploded_boms:
                    # If the operations of the parent BoM and phantom BoM are the same, don't recreate work orders.
                    if not (bom.operation_ids and (not bom_data['parent_line'] or bom_data['parent_line'].bom_id.operation_ids != bom.operation_ids)):
                        continue
                    for operation in bom.operation_ids:
                        if operation._skip_operation_line(bom_data['product']):
                            continue
                        workorders_values += [{
                            'name': operation.name,
                            'production_id': production.id,
                            'workcenter_id': operation.workcenter_id.id,
                            'product_uom_id': production.product_uom_id.id,
                            'operation_id': operation.id,
                            'state': 'pending',
                        }]
                workorders_dict = {wo.operation_id.id: wo for wo in production.workorder_ids.filtered(lambda wo: wo.operation_id)}
                for workorder_values in workorders_values:
                    if workorder_values['operation_id'] in workorders_dict:
                        # update existing entries
                        workorders_list += [Command.update(workorders_dict[workorder_values['operation_id']].id, workorder_values)]
                    else:
                        # add new entries
                        workorders_list += [Command.create(workorder_values)]
                production.workorder_ids = workorders_list
            else:
                production.workorder_ids = [Command.delete(wo.id) for wo in production.workorder_ids.filtered(lambda wo: wo.operation_id)]

    @api.depends('state', 'move_raw_ids.state')
    def _compute_reservation_state(self):
        self.reservation_state = False
        for production in self:
            if production.state in ('draft', 'done', 'cancel'):
                continue
            relevant_move_state = production.move_raw_ids._get_relevant_state_among_moves()
            # Compute reservation state according to its component's moves.
            if relevant_move_state == 'partially_available':
                if production.workorder_ids.operation_id and production.bom_id.ready_to_produce == 'asap':
                    production.reservation_state = production._get_ready_to_produce_state()
                else:
                    production.reservation_state = 'confirmed'
            elif relevant_move_state != 'draft':
                production.reservation_state = relevant_move_state

    @api.depends('move_raw_ids', 'state', 'move_raw_ids.product_uom_qty')
    def _compute_unreserve_visible(self):
        for order in self:
            already_reserved = order.state not in ('done', 'cancel') and order.mapped('move_raw_ids.move_line_ids')
            any_quantity_done = any(m.quantity_done > 0 for m in order.move_raw_ids)

            order.unreserve_visible = not any_quantity_done and already_reserved
            order.reserve_visible = order.state in ('confirmed', 'progress', 'to_close') and any(move.product_uom_qty and move.state in ['confirmed', 'partially_available'] for move in order.move_raw_ids)

    @api.depends('workorder_ids.state', 'move_finished_ids', 'move_finished_ids.quantity_done')
    def _get_produced_qty(self):
        for production in self:
            done_moves = production.move_finished_ids.filtered(lambda x: x.state != 'cancel' and x.product_id.id == production.product_id.id)
            qty_produced = sum(done_moves.mapped('quantity_done'))
            production.qty_produced = qty_produced
        return True

    def _compute_scrap_move_count(self):
        data = self.env['stock.scrap']._read_group([('production_id', 'in', self.ids)], ['production_id'], ['production_id'])
        count_data = dict((item['production_id'][0], item['production_id_count']) for item in data)
        for production in self:
            production.scrap_count = count_data.get(production.id, 0)

    @api.depends('unbuild_ids')
    def _compute_unbuild_count(self):
        for production in self:
            production.unbuild_count = len(production.unbuild_ids)

    @api.depends('move_finished_ids')
    def _compute_move_byproduct_ids(self):
        for order in self:
            order.move_byproduct_ids = order.move_finished_ids.filtered(lambda m: m.product_id != order.product_id)

    def _set_move_byproduct_ids(self):
        move_finished_ids = self.move_finished_ids.filtered(lambda m: m.product_id == self.product_id)
        # TODO: Try to create by-product moves here instead of moving them in the `create`.
        self.move_finished_ids = move_finished_ids | self.move_byproduct_ids

    @api.depends('state')
    def _compute_show_lock(self):
        for order in self:
            order.show_lock = order.state == 'done' or (
                not self.env.user.has_group('mrp.group_unlocked_by_default')
                and order.id is not False
                and order.state not in {'cancel', 'draft'}
            )

    @api.depends('state', 'move_raw_ids')
    def _compute_show_lot_ids(self):
        for order in self:
            order.show_lot_ids = order.state != 'draft' and any(m.product_id.tracking != 'none' for m in order.move_raw_ids)

    @api.depends('state', 'move_raw_ids')
    def _compute_show_serial_mass_produce(self):
        self.show_serial_mass_produce = False
        for order in self:
            if order.state == 'confirmed' and order.product_id.tracking == 'serial' and \
                    float_compare(order.product_qty, 1, precision_rounding=order.product_uom_id.rounding) > 0 and \
                    float_compare(order.qty_producing, order.product_qty, precision_rounding=order.product_uom_id.rounding) < 0:
                order.show_serial_mass_produce = True

    @api.depends('state', 'move_finished_ids')
    def _compute_show_allocation(self):
        self.show_allocation = False
        if not self.user_has_groups('mrp.group_mrp_reception_report'):
            return
        for mo in self:
            if not mo.picking_type_id:
                return
            lines = mo.move_finished_ids.filtered(lambda m: m.product_id.type == 'product' and m.state != 'cancel')
            if lines:
                allowed_states = ['confirmed', 'partially_available', 'waiting']
                if mo.state == 'done':
                    allowed_states += ['assigned']
                wh_location_ids = self.env['stock.location']._search([('id', 'child_of', mo.picking_type_id.warehouse_id.view_location_id.id), ('usage', '!=', 'supplier')])
                if self.env['stock.move'].search([
                    ('state', 'in', allowed_states),
                    ('product_qty', '>', 0),
                    ('location_id', 'in', wh_location_ids),
                    ('raw_material_production_id', '!=', mo.id),
                    ('product_id', 'in', lines.product_id.ids),
                    '|', ('move_orig_ids', '=', False),
                        ('move_orig_ids', 'in', lines.ids)], limit=1):
                    mo.show_allocation = True

    @api.depends('product_uom_qty', 'date_planned_start')
    def _compute_forecasted_issue(self):
        for order in self:
            warehouse = order.location_dest_id.warehouse_id
            order.forecasted_issue = False
            if order.product_id:
                virtual_available = order.product_id.with_context(warehouse=warehouse.id, to_date=order.date_planned_start).virtual_available
                if order.state == 'draft':
                    virtual_available += order.product_uom_qty
                if virtual_available < 0:
                    order.forecasted_issue = True

    @api.model
    def _search_delay_alert_date(self, operator, value):
        late_stock_moves = self.env['stock.move'].search([('delay_alert_date', operator, value)])
        return ['|', ('move_raw_ids', 'in', late_stock_moves.ids), ('move_finished_ids', 'in', late_stock_moves.ids)]

    @api.depends('company_id', 'date_planned_start', 'is_planned', 'product_id')
    def _compute_date_planned_finished(self):
        for production in self:
            if not production.date_planned_start or production.is_planned:
                continue
            days_delay = production.product_id.produce_delay
            date_planned_finished = production.date_planned_start + relativedelta(days=days_delay)
            if date_planned_finished == production.date_planned_start:
                date_planned_finished = date_planned_finished + relativedelta(hours=1)
            production.date_planned_finished = date_planned_finished

    @api.depends('company_id', 'bom_id', 'product_id', 'product_qty', 'product_uom_id', 'location_src_id', 'date_planned_start')
    def _compute_move_raw_ids(self):
        for production in self:
            if production.state != 'draft':
                continue
            list_move_raw = [Command.link(move.id) for move in production.move_raw_ids.filtered(lambda m: not m.bom_line_id)]
            if not production.bom_id and not production._origin.product_id:
                production.move_raw_ids = list_move_raw
            if production.product_id != production._origin.product_id:
                production.move_raw_ids = [Command.clear()]
            if production.bom_id and production.product_id and production.product_qty > 0:
                # keep manual entries
                moves_raw_values = production._get_moves_raw_values()
                move_raw_dict = {move.bom_line_id.id: move for move in production.move_raw_ids.filtered(lambda m: m.bom_line_id)}
                for move_raw_values in moves_raw_values:
                    if move_raw_values['bom_line_id'] in move_raw_dict:
                        # update existing entries
                        list_move_raw += [Command.update(move_raw_dict[move_raw_values['bom_line_id']].id, move_raw_values)]
                    else:
                        # add new entries
                        list_move_raw += [Command.create(move_raw_values)]
                production.move_raw_ids = list_move_raw
            else:
                production.move_raw_ids = [Command.delete(move.id) for move in production.move_raw_ids.filtered(lambda m: m.bom_line_id)]

    @api.depends('product_id', 'bom_id', 'product_qty', 'product_uom_id', 'location_dest_id', 'date_planned_finished')
    def _compute_move_finished_ids(self):
        for production in self:
            if production.state != 'draft':
                updated_values = {}
                if production.date_planned_finished:
                    updated_values['date'] = production.date_planned_finished
                if production.date_deadline:
                    updated_values['date_deadline'] = production.date_deadline
                if 'date' in updated_values or 'date_deadline' in updated_values:
                    production.move_finished_ids = [
                        Command.update(m.id, updated_values) for m in production.move_finished_ids
                    ]
                continue
            production.move_finished_ids = [Command.clear()]
            if production.product_id:
                production._create_update_move_finished()
            else:
                production.move_finished_ids = [
                    Command.delete(move.id) for move in production.move_finished_ids if move.bom_line_id
                ]

    @api.onchange('qty_producing', 'lot_producing_id')
    def _onchange_producing(self):
        self._set_qty_producing()

    @api.onchange('lot_producing_id')
    def _onchange_lot_producing(self):
        if self.product_id.tracking == 'serial' and self.lot_producing_id:
            message, dummy = self.env['stock.quant'].sudo()._check_serial_number(self.product_id,
                                                                                 self.lot_producing_id,
                                                                                 self.company_id)
            if message:
                return {'warning': {'title': _('Warning'), 'message': message}}

    @api.onchange('product_id', 'move_raw_ids')
    def _onchange_product_id(self):
        for move in self.move_raw_ids:
            if self.product_id == move.product_id:
                message = _("The component %s should not be the same as the product to produce.", self.product_id.display_name)
                self.move_raw_ids = self.move_raw_ids - move
                return {'warning': {'title': _('Warning'), 'message': message}}

    @api.constrains('move_byproduct_ids')
    def _check_byproducts(self):
        for order in self:
            if any(move.cost_share < 0 for move in order.move_byproduct_ids):
                raise ValidationError(_("By-products cost shares must be positive."))
            if sum(order.move_byproduct_ids.mapped('cost_share')) > 100:
                raise ValidationError(_("The total cost share for a manufacturing order's by-products cannot exceed 100."))

    def write(self, vals):
        if 'move_byproduct_ids' in vals and 'move_finished_ids' not in vals:
            vals['move_finished_ids'] = vals.get('move_finished_ids', []) + vals['move_byproduct_ids']
            del vals['move_byproduct_ids']
        if 'workorder_ids' in self:
            production_to_replan = self.filtered(lambda p: p.is_planned)
        if 'move_raw_ids' in vals and self.state not in ['draft', 'cancel', 'done']:
            # When adding a move raw, it should have the source location's `warehouse_id`.
            # Before, it was handle by an onchange, now it's forced if not already in vals.
            warehouse_id = self.location_src_id.warehouse_id.id
            if vals.get('location_src_id'):
                location_source = self.env['stock.location'].browse(vals.get('location_src_id'))
                warehouse_id = location_source.warehouse_id.id
            for move_vals in vals['move_raw_ids']:
                command, _id, field_values = move_vals
                if command == Command.CREATE and not field_values.get('warehouse_id', False):
                    field_values['warehouse_id'] = warehouse_id

        res = super(MrpProduction, self).write(vals)

        for production in self:
            if 'date_planned_start' in vals and not self.env.context.get('force_date', False):
                if production.state in ['done', 'cancel']:
                    raise UserError(_('You cannot move a manufacturing order once it is cancelled or done.'))
                if production.is_planned:
                    production.button_unplan()
            if vals.get('date_planned_start'):
                production.move_raw_ids.write({'date': production.date_planned_start, 'date_deadline': production.date_planned_start})
            if vals.get('date_planned_finished'):
                production.move_finished_ids.write({'date': production.date_planned_finished})
            if any(field in ['move_raw_ids', 'move_finished_ids', 'workorder_ids'] for field in vals) and production.state != 'draft':
                production._autoconfirm_production()
                if production in production_to_replan:
                    production._plan_workorders()
            if production.state == 'done' and ('lot_producing_id' in vals or 'qty_producing' in vals):
                finished_move_lines = production.move_finished_ids.filtered(
                    lambda move: move.product_id == production.product_id and move.state == 'done').mapped('move_line_ids')
                if 'lot_producing_id' in vals:
                    finished_move_lines.write({'lot_id': vals.get('lot_producing_id')})
                if 'qty_producing' in vals:
                    finished_move_lines.write({'qty_done': vals.get('qty_producing')})
            if self._has_workorders() and not production.workorder_ids.operation_id and vals.get('date_planned_start') and not vals.get('date_planned_finished'):
                new_date_planned_start = fields.Datetime.to_datetime(vals.get('date_planned_start'))
                if not production.date_planned_finished or new_date_planned_start >= production.date_planned_finished:
                    production.date_planned_finished = new_date_planned_start + datetime.timedelta(hours=1)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Remove from `move_finished_ids` the by-product moves and then move `move_byproduct_ids`
            # into `move_finished_ids` to avoid duplicate and inconsistency.
            if vals.get('move_finished_ids', False) and vals.get('move_byproduct_ids', False):
                vals['move_finished_ids'] = list(filter(lambda move: move[2]['product_id'] == vals['product_id'], vals['move_finished_ids']))
                vals['move_finished_ids'] = vals.get('move_finished_ids', []) + vals['move_byproduct_ids']
                del vals['move_byproduct_ids']
            if not vals.get('name', False) or vals['name'] == _('New'):
                picking_type_id = vals.get('picking_type_id')
                if not picking_type_id:
                    picking_type_id = self._get_default_picking_type_id(vals.get('company_id', self.env.company.id))
                    vals['picking_type_id'] = picking_type_id
                vals['name'] = self.env['stock.picking.type'].browse(picking_type_id).sequence_id.next_by_id()
            if not vals.get('procurement_group_id'):
                procurement_group_vals = self._prepare_procurement_group_vals(vals)
                vals['procurement_group_id'] = self.env["procurement.group"].create(procurement_group_vals).id
        return super().create(vals_list)

    def unlink(self):
        self.action_cancel()
        workorders_to_delete = self.workorder_ids.filtered(lambda wo: wo.state != 'done')
        if workorders_to_delete:
            workorders_to_delete.unlink()
        return super(MrpProduction, self).unlink()

    def copy_data(self, default=None):
        default = dict(default or {})
        # covers at least 2 cases: backorders generation (follow default logic for moves copying)
        # and copying a done MO via the form (i.e. copy only the non-cancelled moves since no backorder = cancelled finished moves)
        if not default or 'move_finished_ids' not in default:
            move_finished_ids = self.move_finished_ids
            if self.state != 'cancel':
                move_finished_ids = self.move_finished_ids.filtered(lambda m: m.state != 'cancel' and m.product_qty != 0.0)
            default['move_finished_ids'] = [(0, 0, move.copy_data()[0]) for move in move_finished_ids]
        if not default or 'move_raw_ids' not in default:
            default['move_raw_ids'] = [(0, 0, move.copy_data()[0]) for move in self.move_raw_ids.filtered(lambda m: m.product_qty != 0.0)]
        return super(MrpProduction, self).copy_data(default=default)

    def copy(self, default=None):
        res = super().copy(default)
        if self.workorder_ids.blocked_by_workorder_ids:
            workorders_mapping = {}
            for original, copied in zip(self.workorder_ids, res.workorder_ids.sorted()):
                workorders_mapping[original] = copied
            for workorder in self.workorder_ids:
                if workorder.blocked_by_workorder_ids:
                    copied_workorder = workorders_mapping[workorder]
                    dependencies = []
                    for dependency in workorder.blocked_by_workorder_ids:
                        dependencies.append(Command.link(workorders_mapping[dependency].id))
                    copied_workorder.blocked_by_workorder_ids = dependencies
        return res

    def action_view_mo_delivery(self):
        """ Returns an action that display picking related to manufacturing order.
        It can either be a list view or in a form view (if there is only one picking to show).
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
        if len(self.picking_ids) > 1:
            action['domain'] = [('id', 'in', self.picking_ids.ids)]
        elif self.picking_ids:
            action['res_id'] = self.picking_ids.id
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                action['views'] += [(state, view) for state, view in action['views'] if view != 'form']
        action['context'] = dict(self._context, default_origin=self.name)
        return action

    def action_toggle_is_locked(self):
        self.ensure_one()
        self.is_locked = not self.is_locked
        return True

    def action_product_forecast_report(self):
        self.ensure_one()
        action = self.product_id.action_product_forecast_report()
        action['context'] = {
            'active_id': self.product_id.id,
            'active_model': 'product.product',
            'move_to_match_ids': self.move_finished_ids.filtered(lambda m: m.product_id == self.product_id).ids
        }
        warehouse = self.picking_type_id.warehouse_id
        if warehouse:
            action['context']['warehouse'] = warehouse.id
        return action

    @api.model
    def _get_default_picking_type_id(self, company_id):
        return self.env['stock.picking.type'].search([
            ('code', '=', 'mrp_operation'),
            ('warehouse_id.company_id', '=', company_id),
        ], limit=1).id

    def _get_move_finished_values(self, product_id, product_uom_qty, product_uom, operation_id=False, byproduct_id=False, cost_share=0):
        group_orders = self.procurement_group_id.mrp_production_ids
        move_dest_ids = self.move_dest_ids
        if len(group_orders) > 1:
            move_dest_ids |= group_orders[0].move_finished_ids.filtered(lambda m: m.product_id == self.product_id).move_dest_ids
        return {
            'product_id': product_id,
            'product_uom_qty': product_uom_qty,
            'product_uom': product_uom,
            'operation_id': operation_id,
            'byproduct_id': byproduct_id,
            'name': _('New'),
            'date': self._get_date_planned_finished(),
            'date_deadline': self.date_deadline,
            'picking_type_id': self.picking_type_id.id,
            'location_id': self.product_id.with_company(self.company_id).property_stock_production.id,
            'location_dest_id': self.location_dest_id.id,
            'company_id': self.company_id.id,
            'production_id': self.id,
            'warehouse_id': self.location_dest_id.warehouse_id.id,
            'origin': self.product_id.partner_ref,
            'group_id': self.procurement_group_id.id,
            'propagate_cancel': self.propagate_cancel,
            'move_dest_ids': [(4, x.id) for x in self.move_dest_ids if not byproduct_id],
            'cost_share': cost_share,
        }

    def _get_date_planned_finished(self):
        date_planned_finished = self.date_planned_start + relativedelta(days=self.product_id.produce_delay)
        if date_planned_finished == self.date_planned_start:
            date_planned_finished = date_planned_finished + relativedelta(hours=1)
        return date_planned_finished

    def _get_moves_finished_values(self):
        moves = []
        for production in self:
            if production.product_id in production.bom_id.byproduct_ids.mapped('product_id'):
                raise UserError(_("You cannot have %s  as the finished product and in the Byproducts", self.product_id.name))
            moves.append(production._get_move_finished_values(production.product_id.id, production.product_qty, production.product_uom_id.id))
            for byproduct in production.bom_id.byproduct_ids:
                if byproduct._skip_byproduct_line(production.product_id):
                    continue
                product_uom_factor = production.product_uom_id._compute_quantity(production.product_qty, production.bom_id.product_uom_id)
                qty = byproduct.product_qty * (product_uom_factor / production.bom_id.product_qty)
                moves.append(production._get_move_finished_values(
                    byproduct.product_id.id, qty, byproduct.product_uom_id.id,
                    byproduct.operation_id.id, byproduct.id, byproduct.cost_share))
        return moves

    def _create_update_move_finished(self):
        """ This is a helper function to support complexity of onchange logic for MOs.
        It is important that the special *2Many commands used here remain as long as function
        is used within onchanges.
        """
        list_move_finished = []
        moves_finished_values = self._get_moves_finished_values()
        moves_byproduct_dict = {move.byproduct_id.id: move for move in self.move_finished_ids.filtered(lambda m: m.byproduct_id)}
        move_finished = self.move_finished_ids.filtered(lambda m: m.product_id == self.product_id)
        for move_finished_values in moves_finished_values:
            if move_finished_values.get('byproduct_id') in moves_byproduct_dict:
                # update existing entries
                list_move_finished += [Command.update(moves_byproduct_dict[move_finished_values['byproduct_id']].id, move_finished_values)]
            elif move_finished_values.get('product_id') == self.product_id.id and move_finished:
                list_move_finished += [Command.update(move_finished.id, move_finished_values)]
            else:
                # add new entries
                list_move_finished += [Command.create(move_finished_values)]
        self.move_finished_ids = list_move_finished

    def _get_moves_raw_values(self):
        moves = []
        for production in self:
            if not production.bom_id:
                continue
            factor = production.product_uom_id._compute_quantity(production.product_qty, production.bom_id.product_uom_id) / production.bom_id.product_qty
            boms, lines = production.bom_id.explode(production.product_id, factor, picking_type=production.bom_id.picking_type_id)
            for bom_line, line_data in lines:
                if bom_line.child_bom_id and bom_line.child_bom_id.type == 'phantom' or\
                        bom_line.product_id.type not in ['product', 'consu']:
                    continue
                operation = bom_line.operation_id.id or line_data['parent_line'] and line_data['parent_line'].operation_id.id
                moves.append(production._get_move_raw_values(
                    bom_line.product_id,
                    line_data['qty'],
                    bom_line.product_uom_id,
                    operation,
                    bom_line
                ))
        return moves

    def _get_move_raw_values(self, product_id, product_uom_qty, product_uom, operation_id=False, bom_line=False):
        """ Warning, any changes done to this method will need to be repeated for consistency in:
            - Manually added components, i.e. "default_" values in view
            - Moves from a copied MO, i.e. move.create
            - Existing moves during backorder creation """
        source_location = self.location_src_id
        data = {
            'sequence': bom_line.sequence if bom_line else 10,
            'name': _('New'),
            'date': self.date_planned_start,
            'date_deadline': self.date_planned_start,
            'bom_line_id': bom_line.id if bom_line else False,
            'picking_type_id': self.picking_type_id.id,
            'product_id': product_id.id,
            'product_uom_qty': product_uom_qty,
            'product_uom': product_uom.id,
            'location_id': source_location.id,
            'location_dest_id': self.product_id.with_company(self.company_id).property_stock_production.id,
            'raw_material_production_id': self.id,
            'company_id': self.company_id.id,
            'operation_id': operation_id,
            'price_unit': product_id.standard_price,
            'procure_method': 'make_to_stock',
            'origin': self._get_origin(),
            'state': 'draft',
            'warehouse_id': source_location.warehouse_id.id,
            'group_id': self.procurement_group_id.id,
            'propagate_cancel': self.propagate_cancel,
        }
        return data

    def _get_origin(self):
        origin = self.name
        if self.orderpoint_id and self.origin:
            origin = self.origin.replace(
                '%s - ' % (self.orderpoint_id.display_name), '')
            origin = '%s,%s' % (origin, self.name)
        return origin

    def _set_qty_producing(self):
        if self.product_id.tracking == 'serial':
            qty_producing_uom = self.product_uom_id._compute_quantity(self.qty_producing, self.product_id.uom_id, rounding_method='HALF-UP')
            if qty_producing_uom != 1:
                self.qty_producing = self.product_id.uom_id._compute_quantity(1, self.product_uom_id, rounding_method='HALF-UP')

        for move in (self.move_raw_ids | self.move_finished_ids.filtered(lambda m: m.product_id != self.product_id)):
            if move._should_bypass_set_qty_producing() or not move.product_uom:
                continue

            new_qty = float_round((self.qty_producing - self.qty_produced) * move.unit_factor, precision_rounding=move.product_uom.rounding)
            if self.use_auto_consume_components_lots and move.has_tracking in ('lot', 'serial'):
                if float_compare(move.reserved_availability, 0, precision_rounding=move.product_uom.rounding) <= 0:
                    continue
                else:
                    new_qty = min(new_qty, move.reserved_availability)

            move.move_line_ids.filtered(lambda ml: ml.state not in ('done', 'cancel')).qty_done = 0
            move.move_line_ids = move._set_quantity_done_prepare_vals(new_qty)

    def _update_raw_moves(self, factor):
        self.ensure_one()
        update_info = []
        move_to_unlink = self.env['stock.move']
        moves_to_assign = self.env['stock.move']
        procurements = []
        for move in self.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
            old_qty = move.product_uom_qty
            new_qty = float_round(old_qty * factor, precision_rounding=move.product_uom.rounding, rounding_method='UP')
            if new_qty > 0:
                move.write({'product_uom_qty': new_qty})
                if move._should_bypass_reservation() \
                        or move.picking_type_id.reservation_method == 'at_confirm' \
                        or (move.reservation_date and move.reservation_date <= fields.Date.today()):
                    moves_to_assign |= move
                if move.procure_method == 'make_to_order':
                    procurement_qty = new_qty - old_qty
                    values = move._prepare_procurement_values()
                    procurements.append(self.env['procurement.group'].Procurement(
                        move.product_id, procurement_qty, move.product_uom,
                        move.location_id, move.name, move.origin, move.company_id, values))
                update_info.append((move, old_qty, new_qty))
            else:
                if move.quantity_done > 0:
                    raise UserError(_('Lines need to be deleted, but can not as you still have some quantities to consume in them. '))
                move._action_cancel()
                move_to_unlink |= move

        moves_to_assign._action_assign()
        move_to_unlink.unlink()
        if procurements:
            self.env['procurement.group'].run(procurements)
        return update_info

    @api.ondelete(at_uninstall=False)
    def _unlink_except_done(self):
        if any(production.state == 'done' for production in self):
            raise UserError(_('Cannot delete a manufacturing order in done state.'))
        not_cancel = self.filtered(lambda m: m.state != 'cancel')
        if not_cancel:
            productions_name = ', '.join([prod.display_name for prod in not_cancel])
            raise UserError(_('%s cannot be deleted. Try to cancel them before.', productions_name))

    def _get_ready_to_produce_state(self):
        """ returns 'assigned' if enough components are reserved in order to complete
        the first operation of the bom. If not returns 'waiting'
        """
        self.ensure_one()
        operations = self.workorder_ids.operation_id
        if len(operations) == 1:
            moves_in_first_operation = self.move_raw_ids
        else:
            first_operation = operations[0]
            moves_in_first_operation = self.move_raw_ids.filtered(lambda move: move.operation_id == first_operation)
        moves_in_first_operation = moves_in_first_operation.filtered(
            lambda move: move.bom_line_id and
            not move.bom_line_id._skip_bom_line(self.product_id)
        )

        if all(move.state == 'assigned' for move in moves_in_first_operation):
            return 'assigned'
        return 'confirmed'

    def _autoconfirm_production(self):
        """Automatically run `action_confirm` on `self`.

        If the production has one of its move was added after the initial call
        to `action_confirm`.
        """
        moves_to_confirm = self.env['stock.move']
        for production in self:
            if production.state in ('done', 'cancel'):
                continue
            additional_moves = production.move_raw_ids.filtered(
                lambda move: move.state == 'draft'
            )
            additional_moves._adjust_procure_method()
            moves_to_confirm |= additional_moves
            additional_byproducts = production.move_finished_ids.filtered(
                lambda move: move.state == 'draft'
            )
            moves_to_confirm |= additional_byproducts

        if moves_to_confirm:
            moves_to_confirm = moves_to_confirm._action_confirm()
            # run scheduler for moves forecasted to not have enough in stock
            moves_to_confirm._trigger_scheduler()

        self.workorder_ids.filtered(lambda w: w.state not in ['done', 'cancel'])._action_confirm()

    def _get_children(self):
        self.ensure_one()
        procurement_moves = self.procurement_group_id.stock_move_ids
        child_moves = procurement_moves.move_orig_ids
        return (procurement_moves | child_moves).created_production_id.procurement_group_id.mrp_production_ids.filtered(lambda p: p.origin != self.origin) - self

    def _get_sources(self):
        self.ensure_one()
        dest_moves = self.procurement_group_id.mrp_production_ids.move_dest_ids
        parent_moves = self.procurement_group_id.stock_move_ids.move_dest_ids
        return (dest_moves | parent_moves).group_id.mrp_production_ids.filtered(lambda p: p.origin != self.origin) - self

    def action_view_mrp_production_childs(self):
        self.ensure_one()
        mrp_production_ids = self._get_children().ids
        action = {
            'res_model': 'mrp.production',
            'type': 'ir.actions.act_window',
        }
        if len(mrp_production_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': mrp_production_ids[0],
            })
        else:
            action.update({
                'name': _("%s Child MO's") % self.name,
                'domain': [('id', 'in', mrp_production_ids)],
                'view_mode': 'tree,form',
            })
        return action

    def action_view_mrp_production_sources(self):
        self.ensure_one()
        mrp_production_ids = self._get_sources().ids
        action = {
            'res_model': 'mrp.production',
            'type': 'ir.actions.act_window',
        }
        if len(mrp_production_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': mrp_production_ids[0],
            })
        else:
            action.update({
                'name': _("MO Generated by %s") % self.name,
                'domain': [('id', 'in', mrp_production_ids)],
                'view_mode': 'tree,form',
            })
        return action

    def action_view_mrp_production_backorders(self):
        backorder_ids = self.procurement_group_id.mrp_production_ids.ids
        return {
            'res_model': 'mrp.production',
            'type': 'ir.actions.act_window',
            'name': _("Backorder MO's"),
            'domain': [('id', 'in', backorder_ids)],
            'view_mode': 'tree,form',
        }

    def action_generate_serial(self):
        self.ensure_one()
        self.lot_producing_id = self.env['stock.lot'].create({
            'product_id': self.product_id.id,
            'company_id': self.company_id.id,
            'name': self.env['stock.lot']._get_next_serial(self.company_id, self.product_id) or self.env['ir.sequence'].next_by_code('stock.lot.serial'),
        })
        if self.move_finished_ids.filtered(lambda m: m.product_id == self.product_id).move_line_ids:
            self.move_finished_ids.filtered(lambda m: m.product_id == self.product_id).move_line_ids.lot_id = self.lot_producing_id
        if self.product_id.tracking == 'serial':
            self._set_qty_producing()

    def _action_generate_immediate_wizard(self):
        view = self.env.ref('mrp.view_immediate_production')
        return {
            'name': _('Immediate Production?'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mrp.immediate.production',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': dict(self.env.context, default_mo_ids=[(4, mo.id) for mo in self]),
        }

    def action_confirm(self):
        self._check_company()
        for production in self:
            if production.bom_id:
                production.consumption = production.bom_id.consumption
            # In case of Serial number tracking, force the UoM to the UoM of product
            if production.product_tracking == 'serial' and production.product_uom_id != production.product_id.uom_id:
                production.write({
                    'product_qty': production.product_uom_id._compute_quantity(production.product_qty, production.product_id.uom_id),
                    'product_uom_id': production.product_id.uom_id
                })
                for move_finish in production.move_finished_ids.filtered(lambda m: m.product_id == production.product_id):
                    move_finish.write({
                        'product_uom_qty': move_finish.product_uom._compute_quantity(move_finish.product_uom_qty, move_finish.product_id.uom_id),
                        'product_uom': move_finish.product_id.uom_id
                    })
            production.move_raw_ids._adjust_procure_method()
            (production.move_raw_ids | production.move_finished_ids)._action_confirm(merge=False)
            production.workorder_ids._action_confirm()
        # run scheduler for moves forecasted to not have enough in stock
        self.move_raw_ids._trigger_scheduler()
        self.picking_ids.filtered(
            lambda p: p.state not in ['cancel', 'done']).action_confirm()
        # Force confirm state only for draft production not for more advanced state like
        # 'progress' (in case of backorders with some qty_producing)
        self.filtered(lambda mo: mo.state == 'draft').state = 'confirmed'
        return True

    def _link_workorders_and_moves(self):
        self.ensure_one()
        if not self.workorder_ids:
            return
        workorder_per_operation = {workorder.operation_id: workorder for workorder in self.workorder_ids}
        workorder_boms = self.workorder_ids.operation_id.bom_id
        last_workorder_per_bom = defaultdict(lambda: self.env['mrp.workorder'])
        self.allow_workorder_dependencies = self.bom_id.allow_operation_dependencies
        if self.allow_workorder_dependencies:
            for workorder in self.workorder_ids:
                workorder.blocked_by_workorder_ids = [Command.link(workorder_per_operation[operation_id].id) for operation_id in workorder.operation_id.blocked_by_operation_ids]
                if not workorder.needed_by_workorder_ids:
                    last_workorder_per_bom[workorder.operation_id.bom_id] = workorder
        else:
            previous_workorder = False
            for workorder in self.workorder_ids:
                if previous_workorder and previous_workorder.operation_id.bom_id == workorder.operation_id.bom_id:
                    workorder.blocked_by_workorder_ids = [Command.link(previous_workorder.id)]
                previous_workorder = workorder
                last_workorder_per_bom[workorder.operation_id.bom_id] = workorder
        for move in (self.move_raw_ids | self.move_finished_ids):
            if move.operation_id:
                move.write({
                    'workorder_id': workorder_per_operation[move.operation_id].id
                })
            else:
                bom = move.bom_line_id.bom_id if (move.bom_line_id and move.bom_line_id.bom_id in workorder_boms) else self.bom_id
                move.write({
                    'workorder_id': last_workorder_per_bom[bom].id
                })

    def action_assign(self):
        for production in self:
            production.move_raw_ids._action_assign()
        return True

    def button_plan(self):
        """ Create work orders. And probably do stuff, like things. """
        orders_to_plan = self.filtered(lambda order: not order.is_planned)
        orders_to_confirm = orders_to_plan.filtered(lambda mo: mo.state == 'draft')
        orders_to_confirm.action_confirm()
        for order in orders_to_plan:
            order._plan_workorders()
        return True

    def _plan_workorders(self, replan=False):
        """ Plan all the production's workorders depending on the workcenters
        work schedule.

        :param replan: If it is a replan, only ready and pending workorder will be taken into account
        :type replan: bool.
        """
        self.ensure_one()

        if not self.workorder_ids:
            return

        self._link_workorders_and_moves()

        # Plan workorders starting from final ones (those with no dependent workorders)
        final_workorders = self.workorder_ids.filtered(lambda wo: not wo.needed_by_workorder_ids)
        for workorder in final_workorders:
            workorder._plan_workorder(replan)

        self.with_context(force_date=True).write({
            'date_planned_start': min([workorder.leave_id.date_from for workorder in self.workorder_ids]),
            'date_planned_finished': max([workorder.leave_id.date_to for workorder in self.workorder_ids])
        })

    def button_unplan(self):
        if any(wo.state == 'done' for wo in self.workorder_ids):
            raise UserError(_("Some work orders are already done, you cannot unplan this manufacturing order."))
        elif any(wo.state == 'progress' for wo in self.workorder_ids):
            raise UserError(_("Some work orders have already started, you cannot unplan this manufacturing order."))

        self.workorder_ids.leave_id.unlink()
        self.workorder_ids.write({
            'date_planned_start': False,
            'date_planned_finished': False,
        })

    def _get_consumption_issues(self):
        """Compare the quantity consumed of the components, the expected quantity
        on the BoM and the consumption parameter on the order.

        :return: list of tuples (order_id, product_id, consumed_qty, expected_qty) where the
            consumption isn't honored. order_id and product_id are recordset of mrp.production
            and product.product respectively
        :rtype: list
        """
        issues = []
        if self.env.context.get('skip_consumption', False) or self.env.context.get('skip_immediate', False):
            return issues
        for order in self:
            if order.consumption == 'flexible' or not order.bom_id or not order.bom_id.bom_line_ids:
                continue
            expected_move_values = order._get_moves_raw_values()
            expected_qty_by_product = defaultdict(float)
            for move_values in expected_move_values:
                move_product = self.env['product.product'].browse(move_values['product_id'])
                move_uom = self.env['uom.uom'].browse(move_values['product_uom'])
                move_product_qty = move_uom._compute_quantity(move_values['product_uom_qty'], move_product.uom_id)
                expected_qty_by_product[move_product] += move_product_qty * order.qty_producing / order.product_qty

            done_qty_by_product = defaultdict(float)
            for move in order.move_raw_ids:
                qty_done = move.product_uom._compute_quantity(move.quantity_done, move.product_id.uom_id)
                rounding = move.product_id.uom_id.rounding
                if not (move.product_id in expected_qty_by_product or float_is_zero(qty_done, precision_rounding=rounding)):
                    issues.append((order, move.product_id, qty_done, 0.0))
                    continue
                done_qty_by_product[move.product_id] += qty_done

            for product, qty_to_consume in expected_qty_by_product.items():
                qty_done = done_qty_by_product.get(product, 0.0)
                if float_compare(qty_to_consume, qty_done, precision_rounding=product.uom_id.rounding) != 0:
                    issues.append((order, product, qty_done, qty_to_consume))

        return issues

    def _action_generate_consumption_wizard(self, consumption_issues):
        ctx = self.env.context.copy()
        lines = []
        for order, product_id, consumed_qty, expected_qty in consumption_issues:
            lines.append((0, 0, {
                'mrp_production_id': order.id,
                'product_id': product_id.id,
                'consumption': order.consumption,
                'product_uom_id': product_id.uom_id.id,
                'product_consumed_qty_uom': consumed_qty,
                'product_expected_qty_uom': expected_qty
            }))
        ctx.update({'default_mrp_production_ids': self.ids,
                    'default_mrp_consumption_warning_line_ids': lines,
                    'form_view_ref': False})
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.action_mrp_consumption_warning")
        action['context'] = ctx
        return action

    def _get_quantity_produced_issues(self):
        quantity_issues = []
        if self.env.context.get('skip_backorder', False):
            return quantity_issues
        for order in self:
            if not float_is_zero(order._get_quantity_to_backorder(), precision_rounding=order.product_uom_id.rounding):
                quantity_issues.append(order)
        return quantity_issues

    def _action_generate_backorder_wizard(self, quantity_issues):
        ctx = self.env.context.copy()
        lines = []
        for order in quantity_issues:
            lines.append((0, 0, {
                'mrp_production_id': order.id,
                'to_backorder': True
            }))
        ctx.update({'default_mrp_production_ids': self.ids, 'default_mrp_production_backorder_line_ids': lines})
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.action_mrp_production_backorder")
        action['context'] = ctx
        return action

    def action_cancel(self):
        """ Cancels production order, unfinished stock moves and set procurement
        orders in exception """
        self._action_cancel()
        return True

    def _action_cancel(self):
        documents_by_production = {}
        for production in self:
            documents = defaultdict(list)
            for move_raw_id in self.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
                iterate_key = self._get_document_iterate_key(move_raw_id)
                if iterate_key:
                    document = self.env['stock.picking']._log_activity_get_documents({move_raw_id: (move_raw_id.product_uom_qty, 0)}, iterate_key, 'UP')
                    for key, value in document.items():
                        documents[key] += [value]
            if documents:
                documents_by_production[production] = documents
            # log an activity on Parent MO if child MO is cancelled.
            finish_moves = production.move_finished_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
            if finish_moves:
                production._log_downside_manufactured_quantity({finish_move: (production.product_uom_qty, 0.0) for finish_move in finish_moves}, cancel=True)

        self.workorder_ids.filtered(lambda x: x.state not in ['done', 'cancel']).action_cancel()
        finish_moves = self.move_finished_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
        raw_moves = self.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
        (finish_moves | raw_moves)._action_cancel()
        picking_ids = self.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
        picking_ids.action_cancel()

        for production, documents in documents_by_production.items():
            filtered_documents = {}
            for (parent, responsible), rendering_context in documents.items():
                if not parent or parent._name == 'stock.picking' and parent.state == 'cancel' or parent == production:
                    continue
                filtered_documents[(parent, responsible)] = rendering_context
            production._log_manufacture_exception(filtered_documents, cancel=True)

        # In case of a flexible BOM, we don't know from the state of the moves if the MO should
        # remain in progress or done. Indeed, if all moves are done/cancel but the quantity produced
        # is lower than expected, it might mean:
        # - we have used all components but we still want to produce the quantity expected
        # - we have used all components and we won't be able to produce the last units
        #
        # However, if the user clicks on 'Cancel', it is expected that the MO is either done or
        # canceled. If the MO is still in progress at this point, it means that the move raws
        # are either all done or a mix of done / canceled => the MO should be done.
        self.filtered(lambda p: p.state not in ['done', 'cancel'] and p.bom_id.consumption == 'flexible').write({'state': 'done'})

        return True

    def _get_document_iterate_key(self, move_raw_id):
        return move_raw_id.move_orig_ids and 'move_orig_ids' or False

    def _cal_price(self, consumed_moves):
        self.ensure_one()
        return True

    def _post_inventory(self, cancel_backorder=False):
        moves_to_do, moves_not_to_do = set(), set()
        for move in self.move_raw_ids:
            if move.state == 'done':
                moves_not_to_do.add(move.id)
            elif move.state != 'cancel':
                moves_to_do.add(move.id)
                if move.product_qty == 0.0 and move.quantity_done > 0:
                    move.product_uom_qty = move.quantity_done
        self.env['stock.move'].browse(moves_to_do)._action_done(cancel_backorder=cancel_backorder)
        moves_to_do = self.move_raw_ids.filtered(lambda x: x.state == 'done') - self.env['stock.move'].browse(moves_not_to_do)
        # Create a dict to avoid calling filtered inside for loops.
        moves_to_do_by_order = defaultdict(lambda: self.env['stock.move'], [
            (key, self.env['stock.move'].concat(*values))
            for key, values in tools_groupby(moves_to_do, key=lambda m: m.raw_material_production_id.id)
        ])
        for order in self:
            finish_moves = order.move_finished_ids.filtered(lambda m: m.product_id == order.product_id and m.state not in ('done', 'cancel'))
            # the finish move can already be completed by the workorder.
            if finish_moves and not finish_moves.quantity_done:
                finish_moves._set_quantity_done(float_round(order.qty_producing - order.qty_produced, precision_rounding=order.product_uom_id.rounding, rounding_method='HALF-UP'))
                finish_moves.move_line_ids.lot_id = order.lot_producing_id
            order._cal_price(moves_to_do_by_order[order.id])
        moves_to_finish = self.move_finished_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
        moves_to_finish = moves_to_finish._action_done(cancel_backorder=cancel_backorder)
        self.action_assign()
        for order in self:
            consume_move_lines = moves_to_do_by_order[order.id].mapped('move_line_ids')
            order.move_finished_ids.move_line_ids.consume_line_ids = [(6, 0, consume_move_lines.ids)]
        return True

    @api.model
    def _get_name_backorder(self, name, sequence):
        if not sequence:
            return name
        seq_back = "-" + "0" * (SIZE_BACK_ORDER_NUMERING - 1 - int(math.log10(sequence))) + str(sequence)
        regex = re.compile(r"-\d+$")
        if regex.search(name) and sequence > 1:
            return regex.sub(seq_back, name)
        return name + seq_back

    def _get_backorder_mo_vals(self):
        self.ensure_one()
        if not self.procurement_group_id:
            # in the rare case that the procurement group has been removed somehow, create a new one
            self.procurement_group_id = self.env["procurement.group"].create({'name': self.name})
        return {
            'procurement_group_id': self.procurement_group_id.id,
            'move_raw_ids': None,
            'move_finished_ids': None,
            'lot_producing_id': False,
            'origin': self.origin,
            'state': 'draft' if self.state == 'draft' else 'confirmed',
            'date_deadline': self.date_deadline,
            'orderpoint_id': self.orderpoint_id.id,
        }

    def _split_productions(self, amounts=False, cancel_remaining_qty=False, set_consumed_qty=False):
        """ Splits productions into productions smaller quantities to produce, i.e. creates
        its backorders.

        :param dict amounts: a dict with a production as key and a list value containing
        the amounts each production split should produce including the original production,
        e.g. {mrp.production(1,): [3, 2]} will result in mrp.production(1,) having a product_qty=3
        and a new backorder with product_qty=2.
        :param bool cancel_remaining_qty: whether to cancel remaining quantities or generate
        an additional backorder, e.g. having product_qty=5 if mrp.production(1,) product_qty was 10.
        :param bool set_consumed_qty: whether to set qty_done on move lines to the reserved quantity
        or the initial demand if no reservation, except for the remaining backorder.
        :return: mrp.production records in order of [orig_prod_1, backorder_prod_1,
        backorder_prod_2, orig_prod_2, backorder_prod_2, etc.]
        """
        def _default_amounts(production):
            return [production.qty_producing, production._get_quantity_to_backorder()]

        if not amounts:
            amounts = {}
        has_backorder_to_ignore = defaultdict(lambda: False)
        for production in self:
            mo_amounts = amounts.get(production)
            if not mo_amounts:
                amounts[production] = _default_amounts(production)
                continue
            total_amount = sum(mo_amounts)
            if total_amount < production.product_qty and not cancel_remaining_qty:
                amounts[production].append(production.product_qty - total_amount)
                has_backorder_to_ignore[production] = True
            elif total_amount > production.product_qty or production.state in ['done', 'cancel']:
                raise UserError(_("Unable to split with more than the quantity to produce."))

        backorder_vals_list = []
        initial_qty_by_production = {}

        # Create the backorders.
        for production in self:
            initial_qty_by_production[production] = production.product_qty
            if production.backorder_sequence == 0:  # Activate backorder naming
                production.backorder_sequence = 1
            production.name = self._get_name_backorder(production.name, production.backorder_sequence)
            (production.move_raw_ids | production.move_finished_ids).name = production.name
            (production.move_raw_ids | production.move_finished_ids).origin = production._get_origin()
            backorder_vals = production.copy_data(default=production._get_backorder_mo_vals())[0]
            backorder_qtys = amounts[production][1:]
            production.product_qty = amounts[production][0]

            next_seq = max(production.procurement_group_id.mrp_production_ids.mapped("backorder_sequence"), default=1)

            for qty_to_backorder in backorder_qtys:
                next_seq += 1
                backorder_vals_list.append(dict(
                    backorder_vals,
                    product_qty=qty_to_backorder,
                    name=production._get_name_backorder(production.name, next_seq),
                    backorder_sequence=next_seq
                ))

        backorders = self.env['mrp.production'].with_context(skip_confirm=True).create(backorder_vals_list)

        index = 0
        production_to_backorders = {}
        production_ids = OrderedSet()
        for production in self:
            number_of_backorder_created = len(amounts.get(production, _default_amounts(production))) - 1
            production_backorders = backorders[index:index + number_of_backorder_created]
            production_to_backorders[production] = production_backorders
            production_ids.update(production.ids)
            production_ids.update(production_backorders.ids)
            index += number_of_backorder_created

        # Split the `stock.move` among new backorders.
        new_moves_vals = []
        moves = []
        move_to_backorder_moves = {}
        for production in self:
            for move in production.move_raw_ids | production.move_finished_ids:
                if move.additional:
                    continue
                move_to_backorder_moves[move] = self.env['stock.move']
                unit_factor = move.product_uom_qty / initial_qty_by_production[production]
                initial_move_vals = move.copy_data(move._get_backorder_move_vals())[0]
                move.with_context(do_not_unreserve=True).product_uom_qty = production.product_qty * unit_factor

                for backorder in production_to_backorders[production]:
                    move_vals = dict(
                        initial_move_vals,
                        product_uom_qty=backorder.product_qty * unit_factor
                    )
                    if move.raw_material_production_id:
                        move_vals['raw_material_production_id'] = backorder.id
                    else:
                        move_vals['production_id'] = backorder.id
                    new_moves_vals.append(move_vals)
                    moves.append(move)

        backorder_moves = self.env['stock.move'].create(new_moves_vals)
        # Split `stock.move.line`s. 2 options for this:
        # - do_unreserve -> action_assign
        # - Split the reserved amounts manually
        # The first option would be easier to maintain since it's less code
        # However it could be slower (due to `stock.quant` update) and could
        # create inconsistencies in mass production if a new lot higher in a
        # FIFO strategy arrives between the reservation and the backorder creation
        for move, backorder_move in zip(moves, backorder_moves):
            move_to_backorder_moves[move] |= backorder_move

        move_lines_vals = []
        assigned_moves = set()
        partially_assigned_moves = set()
        move_lines_to_unlink = set()

        for initial_move, backorder_moves in move_to_backorder_moves.items():
            # Create `stock.move.line` for consumed but non-reserved components
            if initial_move.raw_material_production_id and not initial_move.move_line_ids and set_consumed_qty:
                ml_vals = initial_move._prepare_move_line_vals()
                backorder_move_to_ignore = backorder_moves[-1] if has_backorder_to_ignore[initial_move.raw_material_production_id] else self.env['stock.move']
                for move in list(initial_move + backorder_moves - backorder_move_to_ignore):
                    new_ml_vals = dict(
                        ml_vals,
                        qty_done=move.product_uom_qty,
                        move_id=move.id
                    )
                    move_lines_vals.append(new_ml_vals)

        for initial_move, backorder_moves in move_to_backorder_moves.items():
            ml_by_move = []
            product_uom = initial_move.product_id.uom_id
            for move_line in initial_move.move_line_ids:
                available_qty = move_line.product_uom_id._compute_quantity(move_line.reserved_uom_qty, product_uom)
                if float_compare(available_qty, 0, precision_rounding=move_line.product_uom_id.rounding) <= 0:
                    continue
                ml_by_move.append((available_qty, move_line, move_line.copy_data()[0]))

            initial_move.move_line_ids.with_context(bypass_reservation_update=True).write({'reserved_uom_qty': 0})
            moves = list(initial_move | backorder_moves)

            move = moves and moves.pop(0)
            move_qty_to_reserve = move.product_qty
            for quantity, move_line, ml_vals in ml_by_move:
                while float_compare(quantity, 0, precision_rounding=product_uom.rounding) > 0 and move:
                    # Do not create `stock.move.line` if there is no initial demand on `stock.move`
                    taken_qty = min(move_qty_to_reserve, quantity)
                    taken_qty_uom = product_uom._compute_quantity(taken_qty, move_line.product_uom_id)
                    if move == initial_move:
                        move_line.with_context(bypass_reservation_update=True).reserved_uom_qty = taken_qty_uom
                        if set_consumed_qty:
                            move_line.qty_done = taken_qty_uom
                    elif not float_is_zero(taken_qty_uom, precision_rounding=move_line.product_uom_id.rounding):
                        new_ml_vals = dict(
                            ml_vals,
                            reserved_uom_qty=taken_qty_uom,
                            move_id=move.id
                        )
                        if set_consumed_qty:
                            new_ml_vals['qty_done'] = taken_qty_uom
                        move_lines_vals.append(new_ml_vals)
                    quantity -= taken_qty
                    move_qty_to_reserve -= taken_qty

                    if float_compare(move_qty_to_reserve, 0, precision_rounding=move.product_uom.rounding) <= 0:
                        assigned_moves.add(move.id)
                        move = moves and moves.pop(0)
                        move_qty_to_reserve = move and move.product_qty or 0

                # Unreserve the quantity removed from initial `stock.move.line` and
                # not assigned to a move anymore. In case of a split smaller than initial
                # quantity and fully reserved
                if quantity:
                    self.env['stock.quant']._update_reserved_quantity(
                        move_line.product_id, move_line.location_id, -quantity,
                        lot_id=move_line.lot_id, package_id=move_line.package_id,
                        owner_id=move_line.owner_id, strict=True)

            if move and move_qty_to_reserve != move.product_qty:
                partially_assigned_moves.add(move.id)

            move_lines_to_unlink.update(initial_move.move_line_ids.filtered(
                lambda ml: not ml.reserved_uom_qty and not ml.qty_done).ids)

        self.env['stock.move'].browse(assigned_moves).write({'state': 'assigned'})
        self.env['stock.move'].browse(partially_assigned_moves).write({'state': 'partially_available'})
        # Avoid triggering a useless _recompute_state
        self.env['stock.move.line'].browse(move_lines_to_unlink).write({'move_id': False})
        self.env['stock.move.line'].browse(move_lines_to_unlink).unlink()
        self.env['stock.move.line'].create(move_lines_vals)

        workorders_to_cancel = self.env['mrp.workorder']
        for production in self:
            initial_qty = initial_qty_by_production[production]
            initial_workorder_remaining_qty = []
            bo = production_to_backorders[production]

            # Adapt duration
            for workorder in bo.workorder_ids:
                workorder.duration_expected = workorder._get_duration_expected()

            # Adapt quantities produced
            for workorder in production.workorder_ids:
                initial_workorder_remaining_qty.append(max(initial_qty - workorder.qty_reported_from_previous_wo - workorder.qty_produced, 0))
                workorder.qty_produced = min(workorder.qty_produced, workorder.qty_production)
            workorders_len = len(production.workorder_ids)
            for index, workorder in enumerate(bo.workorder_ids):
                remaining_qty = initial_workorder_remaining_qty[index % workorders_len]
                workorder.qty_reported_from_previous_wo = max(workorder.qty_production - remaining_qty, 0)
                if remaining_qty:
                    initial_workorder_remaining_qty[index % workorders_len] = max(remaining_qty - workorder.qty_produced, 0)
                else:
                    workorders_to_cancel += workorder
        workorders_to_cancel.action_cancel()
        backorders._action_confirm_mo_backorders()

        return self.env['mrp.production'].browse(production_ids)

    def _action_confirm_mo_backorders(self):
        self.workorder_ids._action_confirm()

    def button_mark_done(self):
        self._button_mark_done_sanity_checks()

        if not self.env.context.get('button_mark_done_production_ids'):
            self = self.with_context(button_mark_done_production_ids=self.ids)
        res = self._pre_button_mark_done()
        if res is not True:
            return res

        if self.env.context.get('mo_ids_to_backorder'):
            productions_to_backorder = self.browse(self.env.context['mo_ids_to_backorder'])
            productions_not_to_backorder = self - productions_to_backorder
        else:
            productions_not_to_backorder = self
            productions_to_backorder = self.env['mrp.production']

        self.workorder_ids.button_finish()

        backorders = productions_to_backorder and productions_to_backorder._split_productions()
        backorders = backorders - productions_to_backorder

        productions_not_to_backorder._post_inventory(cancel_backorder=True)
        productions_to_backorder._post_inventory(cancel_backorder=True)

        # if completed products make other confirmed/partially_available moves available, assign them
        done_move_finished_ids = (productions_to_backorder.move_finished_ids | productions_not_to_backorder.move_finished_ids).filtered(lambda m: m.state == 'done')
        done_move_finished_ids._trigger_assign()

        # Moves without quantity done are not posted => set them as done instead of canceling. In
        # case the user edits the MO later on and sets some consumed quantity on those, we do not
        # want the move lines to be canceled.
        (productions_not_to_backorder.move_raw_ids | productions_not_to_backorder.move_finished_ids).filtered(lambda x: x.state not in ('done', 'cancel')).write({
            'state': 'done',
            'product_uom_qty': 0.0,
        })

        for production in self:
            production.write({
                'date_finished': fields.Datetime.now(),
                'product_qty': production.qty_produced,
                'priority': '0',
                'is_locked': True,
                'state': 'done',
            })

        for workorder in self.workorder_ids.filtered(lambda w: w.state not in ('done', 'cancel')):
            workorder.duration_expected = workorder._get_duration_expected()

        if not backorders:
            if self.env.context.get('from_workorder'):
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'mrp.production',
                    'views': [[self.env.ref('mrp.mrp_production_form_view').id, 'form']],
                    'res_id': self.id,
                    'target': 'main',
                }
            if self.user_has_groups('mrp.group_mrp_reception_report') and self.picking_type_id.auto_show_reception_report:
                lines = self.move_finished_ids.filtered(lambda m: m.product_id.type == 'product' and m.state != 'cancel' and m.quantity_done and not m.move_dest_ids)
                if lines:
                    if any(mo.show_allocation for mo in self):
                        action = self.action_view_reception_report()
                        return action
            return True
        context = self.env.context.copy()
        context = {k: v for k, v in context.items() if not k.startswith('default_')}
        for k, v in context.items():
            if k.startswith('skip_'):
                context[k] = False
        action = {
            'res_model': 'mrp.production',
            'type': 'ir.actions.act_window',
            'context': dict(context, mo_ids_to_backorder=None, button_mark_done_production_ids=None)
        }
        if len(backorders) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': backorders[0].id,
            })
        else:
            action.update({
                'name': _("Backorder MO"),
                'domain': [('id', 'in', backorders.ids)],
                'view_mode': 'tree,form',
            })
        return action

    def _pre_button_mark_done(self):
        productions_to_immediate = self._check_immediate()
        if productions_to_immediate:
            return productions_to_immediate._action_generate_immediate_wizard()

        for production in self:
            if float_is_zero(production.qty_producing, precision_rounding=production.product_uom_id.rounding):
                raise UserError(_('The quantity to produce must be positive!'))
            if production.move_raw_ids and not any(production.move_raw_ids.mapped('quantity_done')):
                raise UserError(_("You must indicate a non-zero amount consumed for at least one of your components"))

        consumption_issues = self._get_consumption_issues()
        if consumption_issues:
            return self._action_generate_consumption_wizard(consumption_issues)

        quantity_issues = self._get_quantity_produced_issues()
        if quantity_issues:
            return self._action_generate_backorder_wizard(quantity_issues)
        return True

    def _button_mark_done_sanity_checks(self):
        self._check_company()
        for order in self:
            order._check_sn_uniqueness()

    def do_unreserve(self):
        self.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel'))._do_unreserve()

    def button_scrap(self):
        self.ensure_one()
        return {
            'name': _('Scrap'),
            'view_mode': 'form',
            'res_model': 'stock.scrap',
            'view_id': self.env.ref('stock.stock_scrap_form_view2').id,
            'type': 'ir.actions.act_window',
            'context': {'default_production_id': self.id,
                        'product_ids': (self.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel')) | self.move_finished_ids.filtered(lambda x: x.state == 'done')).mapped('product_id').ids,
                        'default_company_id': self.company_id.id
                        },
            'target': 'new',
        }

    def action_see_move_scrap(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_stock_scrap")
        action['domain'] = [('production_id', '=', self.id)]
        action['context'] = dict(self._context, default_origin=self.name)
        return action

    def action_view_reception_report(self):
        return self.env["ir.actions.actions"]._for_xml_id("mrp.mrp_reception_action")

    def action_view_mrp_production_unbuilds(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.mrp_unbuild")
        action['domain'] = [('mo_id', '=', self.id)]
        context = literal_eval(action['context'])
        context.update(self.env.context)
        context['default_mo_id'] = self.id
        action['context'] = context
        return action

    @api.model
    def get_empty_list_help(self, help):
        self = self.with_context(
            empty_list_help_document_name=_("manufacturing order"),
        )
        return super(MrpProduction, self).get_empty_list_help(help)

    def _log_downside_manufactured_quantity(self, moves_modification, cancel=False):

        def _keys_in_groupby(move):
            """ group by picking and the responsible for the product the
            move.
            """
            return (move.picking_id, move.product_id.responsible_id)

        def _render_note_exception_quantity_mo(rendering_context):
            values = {
                'production_order': self,
                'order_exceptions': rendering_context,
                'impacted_pickings': False,
                'cancel': cancel
            }
            return self.env['ir.qweb']._render('mrp.exception_on_mo', values)

        documents = self.env['stock.picking']._log_activity_get_documents(moves_modification, 'move_dest_ids', 'DOWN', _keys_in_groupby)
        documents = self.env['stock.picking']._less_quantities_than_expected_add_documents(moves_modification, documents)
        self.env['stock.picking']._log_activity(_render_note_exception_quantity_mo, documents)

    def _log_manufacture_exception(self, documents, cancel=False):

        def _render_note_exception_quantity_mo(rendering_context):
            visited_objects = []
            order_exceptions = {}
            for exception in rendering_context:
                order_exception, visited = exception
                order_exceptions.update(order_exception)
                visited_objects += visited
            visited_objects = [sm for sm in visited_objects if sm._name == 'stock.move']
            impacted_object = []
            if visited_objects:
                visited_objects = self.env[visited_objects[0]._name].concat(*visited_objects)
                visited_objects |= visited_objects.mapped('move_orig_ids')
                impacted_object = visited_objects.filtered(lambda m: m.state not in ('done', 'cancel')).mapped('picking_id')
            values = {
                'production_order': self,
                'order_exceptions': order_exceptions,
                'impacted_object': impacted_object,
                'cancel': cancel
            }
            return self.env['ir.qweb']._render('mrp.exception_on_mo', values)

        self.env['stock.picking']._log_activity(_render_note_exception_quantity_mo, documents)

    def button_unbuild(self):
        self.ensure_one()
        return {
            'name': _('Unbuild: %s', self.product_id.display_name),
            'view_mode': 'form',
            'res_model': 'mrp.unbuild',
            'view_id': self.env.ref('mrp.mrp_unbuild_form_view_simplified').id,
            'type': 'ir.actions.act_window',
            'context': {'default_product_id': self.product_id.id,
                        'default_mo_id': self.id,
                        'default_company_id': self.company_id.id,
                        'default_location_id': self.location_dest_id.id,
                        'default_location_dest_id': self.location_src_id.id,
                        'create': False, 'edit': False},
            'target': 'new',
        }

    def action_serial_mass_produce_wizard(self):
        self.ensure_one()
        self._check_company()
        if self.state != 'confirmed':
            return
        if self.product_id.tracking != 'serial':
            return
        if self.reservation_state != 'assigned':
            missing_components = {move.product_id for move in self.move_raw_ids if float_compare(move.reserved_availability, move.product_uom_qty, precision_rounding=move.product_uom.rounding) < 0}
            message = _("Make sure enough quantities of these components are reserved to do the production:\n")
            message += "\n".join(component.name for component in missing_components)
            raise UserError(message)
        next_serial = self.env['stock.lot']._get_next_serial(self.company_id, self.product_id)
        lot_components = {}
        for move in self.move_raw_ids:
            if move.product_id.tracking != 'lot':
                continue
            lot_ids = move.move_line_ids.lot_id.ids
            if not lot_ids:
                continue
            lot_components.setdefault(move.product_id, set()).update(lot_ids)
        multiple_lot_components = set([p for p, l in lot_components.items() if len(l) != 1])
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.act_assign_serial_numbers_production")
        action['context'] = {
            'default_production_id': self.id,
            'default_expected_qty': self.product_qty,
            'default_next_serial_number': next_serial,
            'default_next_serial_count': self.product_qty - self.qty_produced,
            'default_multiple_lot_components_names': ",".join(c.display_name for c in multiple_lot_components) if multiple_lot_components else None,
        }
        return action

    def action_split(self):
        self._pre_action_split_merge_hook(split=True)
        if len(self) > 1:
            productions = [Command.create({'production_id': production.id}) for production in self]
            # Wizard need a real id to have buttons enable in the view
            wizard = self.env['mrp.production.split.multi'].create({'production_ids': productions})
            action = self.env['ir.actions.actions']._for_xml_id('mrp.action_mrp_production_split_multi')
            action['res_id'] = wizard.id
            return action
        else:
            action = self.env['ir.actions.actions']._for_xml_id('mrp.action_mrp_production_split')
            action['context'] = {
                'default_production_id': self.id,
            }
            return action

    def action_merge(self):
        self._pre_action_split_merge_hook(merge=True)
        products = set([(production.product_id, production.bom_id) for production in self])
        product_id, bom_id = products.pop()
        users = set([production.user_id for production in self])
        if len(users) == 1:
            user_id = users.pop()
        else:
            user_id = self.env.user

        origs = self._prepare_merge_orig_links()
        dests = {}
        for move in self.move_finished_ids:
            dests.setdefault(move.byproduct_id.id, []).extend(move.move_dest_ids.ids)

        production = self.env['mrp.production'].with_context(default_picking_type_id=self.picking_type_id.id).create({
            'product_id': product_id.id,
            'bom_id': bom_id.id,
            'picking_type_id': self.picking_type_id.id,
            'product_qty': sum(production.product_uom_qty for production in self),
            'product_uom_id': product_id.uom_id.id,
            'user_id': user_id.id,
            'origin': ",".join(sorted([production.name for production in self])),
        })

        for move in production.move_raw_ids:
            for field, vals in origs[move.bom_line_id.id].items():
                move[field] = vals
        for move in production.move_finished_ids:
            move.move_dest_ids = [Command.set(dests[move.byproduct_id.id])]

        self.move_dest_ids.created_production_id = production.id

        self.procurement_group_id.stock_move_ids.group_id = production.procurement_group_id

        if 'confirmed' in self.mapped('state'):
            production.move_raw_ids._adjust_procure_method()
            (production.move_raw_ids | production.move_finished_ids).write({'state': 'confirmed'})
            production.workorder_ids._action_confirm()
            production.state = 'confirmed'

        self.with_context(skip_activity=True)._action_cancel()
        for p in self:
            p._message_log(body=_('This production has been merge in %s', production.display_name))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'view_mode': 'form',
            'res_id': production.id,
        }

    def _has_workorders(self):
        return self.workorder_ids

    @api.model
    def _prepare_procurement_group_vals(self, values):
        return {'name': values['name']}

    def _get_quantity_to_backorder(self):
        self.ensure_one()
        return max(self.product_qty - self.qty_producing, 0)

    def _check_sn_uniqueness(self):
        """ Alert the user if the serial number as already been consumed/produced """
        if self.product_tracking == 'serial' and self.lot_producing_id:
            if self._is_finished_sn_already_produced(self.lot_producing_id):
                raise UserError(_('This serial number for product %s has already been produced', self.product_id.name))

        for move in self.move_finished_ids:
            if move.has_tracking != 'serial' or move.product_id == self.product_id:
                continue
            for move_line in move.move_line_ids:
                if self._is_finished_sn_already_produced(move_line.lot_id, excluded_sml=move_line):
                    raise UserError(_('The serial number %(number)s used for byproduct %(product_name)s has already been produced',
                                      number=move_line.lot_id.name, product_name=move_line.product_id.name))

        for move in self.move_raw_ids:
            if move.has_tracking != 'serial':
                continue
            for move_line in move.move_line_ids:
                if float_is_zero(move_line.qty_done, precision_rounding=move_line.product_uom_id.rounding):
                    continue
                message = _('The serial number %(number)s used for component %(component)s has already been consumed',
                    number=move_line.lot_id.name,
                    component=move_line.product_id.name)
                co_prod_move_lines = self.move_raw_ids.move_line_ids

                # Check presence of same sn in previous productions
                duplicates = self.env['stock.move.line'].search_count([
                    ('lot_id', '=', move_line.lot_id.id),
                    ('qty_done', '=', 1),
                    ('state', '=', 'done'),
                    ('location_dest_id.usage', '=', 'production'),
                    ('production_id', '!=', False),
                ])
                if duplicates:
                    # Maybe some move lines have been compensated by unbuild
                    duplicates_returned = move.product_id._count_returned_sn_products(move_line.lot_id)
                    removed = self.env['stock.move.line'].search_count([
                        ('lot_id', '=', move_line.lot_id.id),
                        ('state', '=', 'done'),
                        ('location_dest_id.scrap_location', '=', True)
                    ])
                    # Either removed or unbuild
                    if not ((duplicates_returned or removed) and duplicates - duplicates_returned - removed == 0):
                        raise UserError(message)
                # Check presence of same sn in current production
                duplicates = co_prod_move_lines.filtered(lambda ml: ml.qty_done and ml.lot_id == move_line.lot_id) - move_line
                if duplicates:
                    raise UserError(message)

    def _is_finished_sn_already_produced(self, lot, excluded_sml=None):
        excluded_sml = excluded_sml or self.env['stock.move.line']
        domain = [
            ('lot_id', '=', lot.id),
            ('qty_done', '=', 1),
            ('state', '=', 'done')
        ]
        co_prod_move_lines = self.move_finished_ids.move_line_ids - excluded_sml
        domain_unbuild = domain + [
            ('production_id', '=', False),
            ('location_dest_id.usage', '=', 'production')
        ]
        # Check presence of same sn in previous productions
        duplicates = self.env['stock.move.line'].search_count(domain + [
            ('location_id.usage', '=', 'production')
        ])
        if duplicates:
            # Maybe some move lines have been compensated by unbuild
            duplicates_unbuild = self.env['stock.move.line'].search_count(domain_unbuild + [
                ('move_id.unbuild_id', '!=', False)
            ])
            removed = self.env['stock.move.line'].search_count([
                ('lot_id', '=', lot.id),
                ('state', '=', 'done'),
                ('location_dest_id.scrap_location', '=', True)
            ])
            # Either removed or unbuild
            if not ((duplicates_unbuild or removed) and duplicates - duplicates_unbuild - removed == 0):
                return True
        # Check presence of same sn in current production
        duplicates = co_prod_move_lines.filtered(lambda ml: ml.qty_done and ml.lot_id == lot)
        return bool(duplicates)

    def _check_immediate(self):
        immediate_productions = self.browse()
        if self.env.context.get('skip_immediate'):
            return immediate_productions
        pd = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for production in self:
            if all(float_is_zero(ml.qty_done, precision_digits=pd) for
                    ml in production.move_raw_ids.move_line_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
                    ) and float_is_zero(production.qty_producing, precision_digits=pd):
                immediate_productions |= production
        return immediate_productions

    def _pre_action_split_merge_hook(self, merge=False, split=False):
        if not merge and not split:
            return True
        ope_str = merge and _('merged') or _('split')
        if any(production.state not in ('draft', 'confirmed') for production in self):
            raise UserError(_("Only manufacturing orders in either a draft or confirmed state can be %s.", ope_str))
        if any(not production.bom_id for production in self):
            raise UserError(_("Only manufacturing orders with a Bill of Materials can be %s.", ope_str))
        if split:
            return True

        if len(self) < 2:
            raise UserError(_("You need at least two production orders to merge them."))
        products = set([(production.product_id, production.bom_id) for production in self])
        if len(products) > 1:
            raise UserError(_('You can only merge manufacturing orders of identical products with same BoM.'))
        additional_raw_ids = self.mapped("move_raw_ids").filtered(lambda move: not move.bom_line_id)
        additional_byproduct_ids = self.mapped('move_byproduct_ids').filtered(lambda move: not move.byproduct_id)
        if additional_raw_ids or additional_byproduct_ids:
            raise UserError(_("You can only merge manufacturing orders with no additional components or by-products."))
        if len(set(self.mapped('state'))) > 1:
            raise UserError(_("You can only merge manufacturing with the same state."))
        if len(set(self.mapped('picking_type_id'))) > 1:
            raise UserError(_('You can only merge manufacturing with the same operation type'))
        # TODO explode and check no quantity has been edited
        return True

    def _prepare_merge_orig_links(self):
        origs = defaultdict(dict)
        for move in self.move_raw_ids:
            if not move.move_orig_ids:
                continue
            origs[move.bom_line_id.id].setdefault('move_orig_ids', set()).update(move.move_orig_ids.ids)
        for vals in origs.values():
            if not vals.get('move_orig_ids'):
                continue
            vals['move_orig_ids'] = [Command.set(vals['move_orig_ids'])]
        return origs
