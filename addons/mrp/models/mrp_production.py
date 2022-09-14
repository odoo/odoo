# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import datetime
import math
import operator as py_operator
import re

from collections import defaultdict
from dateutil.relativedelta import relativedelta
from itertools import groupby

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_compare, float_round, float_is_zero, format_datetime
from odoo.tools.misc import format_date

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
    def _get_default_picking_type(self):
        company_id = self.env.context.get('default_company_id', self.env.company.id)
        return self.env['stock.picking.type'].search([
            ('code', '=', 'mrp_operation'),
            ('warehouse_id.company_id', '=', company_id),
        ], limit=1).id

    @api.model
    def _get_default_location_src_id(self):
        location = False
        company_id = self.env.context.get('default_company_id', self.env.company.id)
        if self.env.context.get('default_picking_type_id'):
            location = self.env['stock.picking.type'].browse(self.env.context['default_picking_type_id']).default_location_src_id
        if not location:
            location = self.env['stock.warehouse'].search([('company_id', '=', company_id)], limit=1).lot_stock_id
        return location and location.id or False

    @api.model
    def _get_default_location_dest_id(self):
        location = False
        company_id = self.env.context.get('default_company_id', self.env.company.id)
        if self._context.get('default_picking_type_id'):
            location = self.env['stock.picking.type'].browse(self.env.context['default_picking_type_id']).default_location_dest_id
        if not location:
            location = self.env['stock.warehouse'].search([('company_id', '=', company_id)], limit=1).lot_stock_id
        return location and location.id or False

    @api.model
    def _get_default_date_planned_finished(self):
        if self.env.context.get('default_date_planned_start'):
            return fields.Datetime.to_datetime(self.env.context.get('default_date_planned_start')) + datetime.timedelta(hours=1)
        return datetime.datetime.now() + datetime.timedelta(hours=1)

    @api.model
    def _get_default_date_planned_start(self):
        if self.env.context.get('default_date_deadline'):
            return fields.Datetime.to_datetime(self.env.context.get('default_date_deadline'))
        return datetime.datetime.now()

    @api.model
    def _get_default_is_locked(self):
        return self.user_has_groups('mrp.group_locked_by_default')

    name = fields.Char(
        'Reference', copy=False, readonly=True, default=lambda x: _('New'))
    priority = fields.Selection(
        PROCUREMENT_PRIORITIES, string='Priority', default='0', index=True,
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
        readonly=True, required=True, check_company=True,
        states={'draft': [('readonly', False)]})
    product_tracking = fields.Selection(related='product_id.tracking')
    allowed_product_ids = fields.Many2many('product.product', compute='_compute_allowed_product_ids')
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', related='product_id.product_tmpl_id')
    product_qty = fields.Float(
        'Quantity To Produce',
        default=1.0, digits='Product Unit of Measure',
        readonly=True, required=True, tracking=True,
        states={'draft': [('readonly', False)]})
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        readonly=True, required=True,
        states={'draft': [('readonly', False)]}, domain="[('category_id', '=', product_uom_category_id)]")
    lot_producing_id = fields.Many2one(
        'stock.production.lot', string='Lot/Serial Number', copy=False,
        domain="[('product_id', '=', product_id), ('company_id', '=', company_id)]", check_company=True)
    qty_producing = fields.Float(string="Quantity Producing", digits='Product Unit of Measure', copy=False)
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    product_uom_qty = fields.Float(string='Total Quantity', compute='_compute_product_uom_qty', store=True)
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type',
        domain="[('code', '=', 'mrp_operation'), ('company_id', '=', company_id)]",
        default=_get_default_picking_type, required=True, check_company=True,
        readonly=True, states={'draft': [('readonly', False)]})
    use_create_components_lots = fields.Boolean(related='picking_type_id.use_create_components_lots')
    location_src_id = fields.Many2one(
        'stock.location', 'Components Location',
        default=_get_default_location_src_id,
        readonly=True, required=True,
        domain="[('usage','=','internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        states={'draft': [('readonly', False)]}, check_company=True,
        help="Location where the system will look for components.")
    location_dest_id = fields.Many2one(
        'stock.location', 'Finished Products Location',
        default=_get_default_location_dest_id,
        readonly=True, required=True,
        domain="[('usage','=','internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        states={'draft': [('readonly', False)]}, check_company=True,
        help="Location where the system will stock the finished products.")
    date_planned_start = fields.Datetime(
        'Scheduled Date', copy=False, default=_get_default_date_planned_start,
        help="Date at which you plan to start the production.",
        index=True, required=True)
    date_planned_finished = fields.Datetime(
        'Scheduled End Date',
        default=_get_default_date_planned_finished,
        help="Date at which you plan to finish the production.",
        copy=False)
    date_deadline = fields.Datetime(
        'Deadline', copy=False, store=True, readonly=True, compute='_compute_date_deadline', inverse='_set_date_deadline',
        help="Informative date allowing to define when the manufacturing order should be processed at the latest to fulfill delivery on time.")
    date_start = fields.Datetime('Start Date', copy=False, index=True, readonly=True)
    date_finished = fields.Datetime('End Date', copy=False, index=True, readonly=True)
    bom_id = fields.Many2one(
        'mrp.bom', 'Bill of Material',
        readonly=True, states={'draft': [('readonly', False)]},
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
        check_company=True,
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
        string='Material Availability',
        compute='_compute_state', copy=False, index=True, readonly=True,
        store=True, tracking=True,
        help=" * Ready: The material is available to start the production.\n\
            * Waiting: The material is not available to start the production.\n\
            The material availability is impacted by the manufacturing readiness\
            defined on the BoM.")

    move_raw_ids = fields.One2many(
        'stock.move', 'raw_material_production_id', 'Components',
        copy=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        domain=[('scrapped', '=', False)])
    move_finished_ids = fields.One2many(
        'stock.move', 'production_id', 'Finished Products',
        copy=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        domain=[('scrapped', '=', False)])
    move_byproduct_ids = fields.One2many('stock.move', compute='_compute_move_byproduct_ids', inverse='_set_move_byproduct_ids')
    finished_move_line_ids = fields.One2many(
        'stock.move.line', compute='_compute_lines', inverse='_inverse_lines', string="Finished Product"
        )
    workorder_ids = fields.One2many(
        'mrp.workorder', 'production_id', 'Work Orders', copy=True)
    workorder_done_count = fields.Integer('# Done Work Orders', compute='_compute_workorder_done_count')
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
    orderpoint_id = fields.Many2one('stock.warehouse.orderpoint', 'Orderpoint', index=True)
    propagate_cancel = fields.Boolean(
        'Propagate cancel and split',
        help='If checked, when the previous move of the move (which was generated by a next procurement) is cancelled or split, the move generated by this move will too')
    delay_alert_date = fields.Datetime('Delay Alert Date', compute='_compute_delay_alert_date', search='_search_delay_alert_date')
    json_popover = fields.Char('JSON data for the popover widget', compute='_compute_json_popover')
    scrap_ids = fields.One2many('stock.scrap', 'production_id', 'Scraps')
    scrap_count = fields.Integer(compute='_compute_scrap_move_count', string='Scrap Move')
    is_locked = fields.Boolean('Is Locked', default=_get_default_is_locked, copy=False)
    is_planned = fields.Boolean('Its Operations are Planned', compute='_compute_is_planned', search='_search_is_planned')

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
        string="Component Availability", compute='_compute_components_availability')
    components_availability_state = fields.Selection([
        ('available', 'Available'),
        ('expected', 'Expected'),
        ('late', 'Late')], compute='_compute_components_availability')
    show_lot_ids = fields.Boolean('Display the serial number shortcut on the moves', compute='_compute_show_lot_ids')

    @api.depends('product_id', 'bom_id', 'company_id')
    def _compute_allowed_product_ids(self):
        for production in self:
            product_domain = [
                ('type', 'in', ['product', 'consu']),
                '|',
                    ('company_id', '=', False),
                    ('company_id', '=', production.company_id.id)
            ]
            if production.bom_id:
                if production.bom_id.product_id:
                    product_domain += [('id', '=', production.bom_id.product_id.id)]
                else:
                    product_domain += [('id', 'in', production.bom_id.product_tmpl_id.product_variant_ids.ids)]
            production.allowed_product_ids = self.env['product.product'].search(product_domain)

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

    @api.depends('move_raw_ids', 'state', 'date_planned_start', 'move_raw_ids.forecast_availability', 'move_raw_ids.forecast_expected_date')
    def _compute_components_availability(self):
        self.components_availability = False
        self.components_availability_state = 'available'
        productions = self.filtered(lambda mo: mo.state not in ['cancel', 'draft', 'done'])
        productions.components_availability = _('Available')
        for production in productions:
            forecast_date = max(production.move_raw_ids.filtered('forecast_expected_date').mapped('forecast_expected_date'), default=False)
            if any(float_compare(move.forecast_availability, move.product_qty, move.product_id.uom_id.rounding) == -1 for move in production.move_raw_ids):
                production.components_availability = _('Not Available')
                production.components_availability_state = 'late'
            elif forecast_date:
                production.components_availability = _('Exp %s', format_date(self.env, forecast_date))
                production.components_availability_state = 'late' if forecast_date > production.date_planned_start else 'expected'

    @api.depends('move_finished_ids.date_deadline')
    def _compute_date_deadline(self):
        for production in self:
            production.date_deadline = min(production.move_finished_ids.filtered('date_deadline').mapped('date_deadline'), default=production.date_deadline or False)

    def _set_date_deadline(self):
        for production in self:
            production.move_finished_ids.date_deadline = production.date_deadline

    @api.depends("workorder_ids.date_planned_start", "workorder_ids.date_planned_finished")
    def _compute_is_planned(self):
        for production in self:
            if production.workorder_ids:
                production.is_planned = any(wo.date_planned_start and wo.date_planned_finished for wo in production.workorder_ids if wo.state != 'done')
            else:
                production.is_planned = False

    def _search_is_planned(self, operator, value):
        if operator not in ('=', '!='):
            raise UserError(_('Invalid domain operator %s', operator))

        if value not in (False, True):
            raise UserError(_('Invalid domain right operand %s', value))
        ops = {'=': py_operator.eq, '!=': py_operator.ne}
        ids = []
        for mo in self.search([]):
            if ops[operator](value, mo.is_planned):
                ids.append(mo.id)

        return [('id', 'in', ids)]

    @api.depends('move_raw_ids.delay_alert_date')
    def _compute_delay_alert_date(self):
        delay_alert_date_data = self.env['stock.move'].read_group([('id', 'in', self.move_raw_ids.ids), ('delay_alert_date', '!=', False)], ['delay_alert_date:max'], 'raw_material_production_id')
        delay_alert_date_data = {data['raw_material_production_id'][0]: data['delay_alert_date'] for data in delay_alert_date_data}
        for production in self:
            production.delay_alert_date = delay_alert_date_data.get(production.id, False)

    def _compute_json_popover(self):
        for production in self:
            production.json_popover = json.dumps({
                'popoverTemplate': 'stock.PopoverStockRescheduling',
                'delay_alert_date': format_datetime(self.env, production.delay_alert_date, dt_format=False) if production.delay_alert_date else False,
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

    @api.depends('procurement_group_id')
    def _compute_picking_ids(self):
        for order in self:
            order.picking_ids = self.env['stock.picking'].search([
                ('group_id', '=', order.procurement_group_id.id), ('group_id', '!=', False),
            ])
            order.delivery_count = len(order.picking_ids)

    def action_view_mo_delivery(self):
        """ This function returns an action that display picking related to
        manufacturing order orders. It can either be a in a list or in a form
        view, if there is only one picking to show.
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
        pickings = self.mapped('picking_ids')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = pickings.id
        action['context'] = dict(self._context, default_origin=self.name, create=False)
        return action

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
        location_by_company = self.env['stock.location'].read_group([
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

    @api.depends('workorder_ids.state')
    def _compute_workorder_done_count(self):
        data = self.env['mrp.workorder'].read_group([
            ('production_id', 'in', self.ids),
            ('state', '=', 'done')], ['production_id'], ['production_id'])
        count_data = dict((item['production_id'][0], item['production_id_count']) for item in data)
        for production in self:
            production.workorder_done_count = count_data.get(production.id, 0)

    @api.depends(
        'move_raw_ids.state', 'move_raw_ids.quantity_done', 'move_finished_ids.state',
        'workorder_ids', 'workorder_ids.state', 'product_qty', 'qty_producing')
    def _compute_state(self):
        """ Compute the production state. It use the same process than stock
        picking. It exists 3 extra steps for production:
        - progress: At least one item is produced or consumed.
        - to_close: The quantity produced is greater than the quantity to
        produce and all work orders has been finished.
        """
        # TODO: duplicated code with stock_picking.py
        for production in self:
            if not production.move_raw_ids:
                production.state = 'draft'
            elif all(move.state == 'draft' for move in production.move_raw_ids):
                production.state = 'draft'
            elif all(move.state == 'cancel' for move in production.move_raw_ids):
                production.state = 'cancel'
            elif all(move.state in ('cancel', 'done') for move in production.move_raw_ids):
                production.state = 'done'
            elif production.workorder_ids and all(wo_state in ('done', 'cancel') for wo_state in production.workorder_ids.mapped('state')):
                production.state = 'to_close'
            elif not production.workorder_ids and float_compare(production.qty_producing, production.product_qty, precision_rounding=production.product_uom_id.rounding) >= 0:
                production.state = 'to_close'
            elif any(wo_state in ('progress', 'done') for wo_state in production.workorder_ids.mapped('state')):
                production.state = 'progress'
            elif not float_is_zero(production.qty_producing, precision_rounding=production.product_uom_id.rounding):
                production.state = 'progress'
            elif any(not float_is_zero(move.quantity_done, precision_rounding=move.product_uom.rounding or move.product_id.uom_id.rounding) for move in production.move_raw_ids):
                production.state = 'progress'
            else:
                production.state = 'confirmed'

            # Compute reservation state
            # State where the reservation does not matter.
            production.reservation_state = False
            # Compute reservation state according to its component's moves.
            if production.state not in ('draft', 'done', 'cancel'):
                relevant_move_state = production.move_raw_ids._get_relevant_state_among_moves()
                if relevant_move_state == 'partially_available':
                    if production.bom_id.operation_ids and production.bom_id.ready_to_produce == 'asap':
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
        data = self.env['stock.scrap'].read_group([('production_id', 'in', self.ids)], ['production_id'], ['production_id'])
        count_data = dict((item['production_id'][0], item['production_id_count']) for item in data)
        for production in self:
            production.scrap_count = count_data.get(production.id, 0)

    @api.depends('move_finished_ids')
    def _compute_move_byproduct_ids(self):
        for order in self:
            order.move_byproduct_ids = order.move_finished_ids.filtered(lambda m: m.product_id != order.product_id)

    def _set_move_byproduct_ids(self):
        move_finished_ids = self.move_finished_ids.filtered(lambda m: m.product_id == self.product_id)
        self.move_finished_ids = move_finished_ids | self.move_byproduct_ids

    @api.depends('state')
    def _compute_show_lock(self):
        for order in self:
            order.show_lock = self.env.user.has_group('mrp.group_locked_by_default') and order.id is not False and order.state not in {'cancel', 'draft'}

    @api.depends('state','move_raw_ids')
    def _compute_show_lot_ids(self):
        for order in self:
            order.show_lot_ids = order.state != 'draft' and any(m.product_id.tracking == 'serial' for m in order.move_raw_ids)

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Reference must be unique per Company!'),
        ('qty_positive', 'check (product_qty > 0)', 'The quantity to produce must be positive!'),
    ]

    @api.model
    def _search_delay_alert_date(self, operator, value):
        late_stock_moves = self.env['stock.move'].search([('delay_alert_date', operator, value)])
        return ['|', ('move_raw_ids', 'in', late_stock_moves.ids), ('move_finished_ids', 'in', late_stock_moves.ids)]

    @api.onchange('company_id')
    def onchange_company_id(self):
        if self.company_id:
            if self.move_raw_ids:
                self.move_raw_ids.update({'company_id': self.company_id})
            if self.picking_type_id and self.picking_type_id.company_id != self.company_id:
                self.picking_type_id = self.env['stock.picking.type'].search([
                    ('code', '=', 'mrp_operation'),
                    ('warehouse_id.company_id', '=', self.company_id.id),
                ], limit=1).id

    @api.onchange('product_id', 'picking_type_id', 'company_id')
    def onchange_product_id(self):
        """ Finds UoM of changed product. """
        if not self.product_id:
            self.bom_id = False
        elif not self.bom_id or self.bom_id.product_tmpl_id != self.product_tmpl_id or (self.bom_id.product_id and self.bom_id.product_id != self.product_id):
            bom = self.env['mrp.bom']._bom_find(product=self.product_id, picking_type=self.picking_type_id, company_id=self.company_id.id, bom_type='normal')
            if bom:
                self.bom_id = bom.id
                self.product_qty = self.bom_id.product_qty
                self.product_uom_id = self.bom_id.product_uom_id.id
            else:
                self.bom_id = False
                self.product_uom_id = self.product_id.uom_id.id

    @api.onchange('product_qty', 'product_uom_id')
    def _onchange_product_qty(self):
        for workorder in self.workorder_ids:
            workorder.product_uom_id = self.product_uom_id
            if self._origin.product_qty:
                workorder.duration_expected = workorder._get_duration_expected(ratio=self.product_qty / self._origin.product_qty)
            else:
                workorder.duration_expected = workorder._get_duration_expected()
            if workorder.date_planned_start and workorder.duration_expected:
                workorder.date_planned_finished = workorder.date_planned_start + relativedelta(minutes=workorder.duration_expected)

    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        if not self.product_id and self.bom_id:
            self.product_id = self.bom_id.product_id or self.bom_id.product_tmpl_id.product_variant_ids[:1]
        self.product_qty = self.bom_id.product_qty or 1.0
        self.product_uom_id = self.bom_id and self.bom_id.product_uom_id.id or self.product_id.uom_id.id
        self.move_raw_ids = [(2, move.id) for move in self.move_raw_ids.filtered(lambda m: m.bom_line_id)]
        self.move_finished_ids = [(2, move.id) for move in self.move_finished_ids]
        self.picking_type_id = self.bom_id.picking_type_id or self.picking_type_id

    @api.onchange('date_planned_start', 'product_id')
    def _onchange_date_planned_start(self):
        if self.date_planned_start and not self.is_planned:
            date_planned_finished = self.date_planned_start + relativedelta(days=self.product_id.produce_delay)
            date_planned_finished = date_planned_finished + relativedelta(days=self.company_id.manufacturing_lead)
            if date_planned_finished == self.date_planned_start:
                date_planned_finished = date_planned_finished + relativedelta(hours=1)
            self.date_planned_finished = date_planned_finished
            self.move_raw_ids = [(1, m.id, {'date': self.date_planned_start}) for m in self.move_raw_ids]
            self.move_finished_ids = [(1, m.id, {'date': date_planned_finished}) for m in self.move_finished_ids]

    @api.onchange('bom_id', 'product_id', 'product_qty', 'product_uom_id')
    def _onchange_move_raw(self):
        if not self.bom_id and not self._origin.product_id:
            return
        # Clear move raws if we are changing the product. In case of creation (self._origin is empty),
        # we need to avoid keeping incorrect lines, so clearing is necessary too.
        if self.product_id != self._origin.product_id:
            self.move_raw_ids = [(5,)]
        if self.bom_id and self.product_qty > 0:
            # keep manual entries
            list_move_raw = [(4, move.id) for move in self.move_raw_ids.filtered(lambda m: not m.bom_line_id)]
            moves_raw_values = self._get_moves_raw_values()
            move_raw_dict = {move.bom_line_id.id: move for move in self.move_raw_ids.filtered(lambda m: m.bom_line_id)}
            for move_raw_values in moves_raw_values:
                if move_raw_values['bom_line_id'] in move_raw_dict:
                    # update existing entries
                    list_move_raw += [(1, move_raw_dict[move_raw_values['bom_line_id']].id, move_raw_values)]
                else:
                    # add new entries
                    list_move_raw += [(0, 0, move_raw_values)]
            self.move_raw_ids = list_move_raw
        else:
            self.move_raw_ids = [(2, move.id) for move in self.move_raw_ids.filtered(lambda m: m.bom_line_id)]

    @api.onchange('product_id')
    def _onchange_move_finished_product(self):
        self.move_finished_ids = [(5,)]
        if self.product_id:
            self._create_update_move_finished()

    @api.onchange('bom_id', 'product_qty', 'product_uom_id')
    def _onchange_move_finished(self):
        if self.product_id and self.product_qty > 0:
            self._create_update_move_finished()
        else:
            self.move_finished_ids = [(2, move.id) for move in self.move_finished_ids.filtered(lambda m: m.bom_line_id)]

    @api.onchange('location_src_id', 'move_raw_ids', 'bom_id')
    def _onchange_location(self):
        source_location = self.location_src_id
        self.move_raw_ids.update({
            'warehouse_id': source_location.get_warehouse().id,
            'location_id': source_location.id,
        })

    @api.onchange('location_dest_id', 'move_finished_ids', 'bom_id')
    def _onchange_location_dest(self):
        destination_location = self.location_dest_id
        update_value_list = []
        for move in self.move_finished_ids:
            update_value_list += [(1, move.id, ({
                'warehouse_id': destination_location.get_warehouse().id,
                'location_dest_id': destination_location.id,
            }))]
        self.move_finished_ids = update_value_list

    @api.onchange('picking_type_id')
    def onchange_picking_type(self):
        location = self.env.ref('stock.stock_location_stock')
        try:
            location.check_access_rule('read')
        except (AttributeError, AccessError):
            location = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1).lot_stock_id
        self.move_raw_ids.update({'picking_type_id': self.picking_type_id})
        self.move_finished_ids.update({'picking_type_id': self.picking_type_id})
        self.location_src_id = self.picking_type_id.default_location_src_id.id or location.id
        self.location_dest_id = self.picking_type_id.default_location_dest_id.id or location.id

    @api.onchange('qty_producing', 'lot_producing_id')
    def _onchange_producing(self):
        self._set_qty_producing()

    @api.onchange('lot_producing_id')
    def _onchange_lot_producing(self):
        if self.product_id.tracking == 'serial':
            if self.env['stock.move.line'].search([
                ('lot_id', '=', self.lot_producing_id.id),
                ('qty_done', '=', 1),
                ('state', '=', 'done'),
                ('location_id.usage', '!=', 'production'),
                ('location_dest_id.usage', '!=', 'production'),
            ], limit=1) or self._is_finished_sn_already_produced(self.lot_producing_id):
                return {
                    'warning': {
                        'title': _('Warning'),
                        'message': _('Existing Serial number (%s). Please correct the serial numbers encoded.') % self.lot_producing_id.name
                    }
                }

    @api.onchange('bom_id')
    def _onchange_workorder_ids(self):
        if self.bom_id:
            self._create_workorder()
        else:
            self.workorder_ids = False

    @api.constrains('product_id', 'move_raw_ids')
    def _check_production_lines(self):
        for production in self:
            for move in production.move_raw_ids:
                if production.product_id == move.product_id:
                    raise ValidationError(_("The component %s should not be the same as the product to produce.") % production.product_id.display_name)

    def write(self, vals):
        if 'workorder_ids' in self:
            production_to_replan = self.filtered(lambda p: p.is_planned)
        res = super(MrpProduction, self).write(vals)

        for production in self:
            if 'date_planned_start' in vals and not self.env.context.get('force_date', False):
                if production.state in ['done', 'cancel']:
                    raise UserError(_('You cannot move a manufacturing order once it is cancelled or done.'))
                if production.is_planned:
                    production.button_unplan()
                    move_vals = self._get_move_finished_values(self.product_id, self.product_uom_qty, self.product_uom_id)
                    production.move_finished_ids.write({'date': move_vals['date']})
            if vals.get('date_planned_start'):
                production.move_raw_ids.write({'date': production.date_planned_start, 'date_deadline': production.date_planned_start})
            if vals.get('date_planned_finished'):
                production.move_finished_ids.write({'date': production.date_planned_finished})
            if any(field in ['move_raw_ids', 'move_finished_ids', 'workorder_ids'] for field in vals) and production.state != 'draft':
                if production.state == 'done':
                    # for some reason moves added after state = 'done' won't save group_id, reference if added in
                    # "stock_move.default_get()"
                    production.move_raw_ids.filtered(lambda move: move.additional and move.date > production.date_planned_start).write({
                        'group_id': production.procurement_group_id.id,
                        'reference': production.name,
                        'date': production.date_planned_start,
                        'date_deadline': production.date_planned_start
                    })
                    production.move_finished_ids.filtered(lambda move: move.additional and move.date > production.date_planned_finished).write({
                        'reference': production.name,
                        'date': production.date_planned_finished,
                        'date_deadline': production.date_deadline
                    })
                production._autoconfirm_production()
                if production in production_to_replan:
                    production._plan_workorders(replan=True)
            if production.state == 'done' and ('lot_producing_id' in vals or 'qty_producing' in vals):
                finished_move_lines = production.move_finished_ids.filtered(
                    lambda move: move.product_id == self.product_id and move.state == 'done').mapped('move_line_ids')
                if 'lot_producing_id' in vals:
                    finished_move_lines.write({'lot_id': vals.get('lot_producing_id')})
                if 'qty_producing' in vals:
                    finished_move_lines.write({'qty_done': vals.get('qty_producing')})

            if not production.bom_id.operation_ids and vals.get('date_planned_start') and not vals.get('date_planned_finished'):
                new_date_planned_start = fields.Datetime.to_datetime(vals.get('date_planned_start'))
                if not production.date_planned_finished or new_date_planned_start >= production.date_planned_finished:
                    production.date_planned_finished = new_date_planned_start + datetime.timedelta(hours=1)
        return res

    @api.model
    def create(self, values):
        # Remove from `move_finished_ids` the by-product moves and then move `move_byproduct_ids`
        # into `move_finished_ids` to avoid duplicate and inconsistency.
        if values.get('move_finished_ids', False):
            values['move_finished_ids'] = list(filter(lambda move: move[2]['byproduct_id'] is False, values['move_finished_ids']))
        if values.get('move_byproduct_ids', False):
            values['move_finished_ids'] = values.get('move_finished_ids', []) + values['move_byproduct_ids']
            del values['move_byproduct_ids']
        if not values.get('name', False) or values['name'] == _('New'):
            picking_type_id = values.get('picking_type_id') or self._get_default_picking_type()
            picking_type_id = self.env['stock.picking.type'].browse(picking_type_id)
            if picking_type_id:
                values['name'] = picking_type_id.sequence_id.next_by_id()
            else:
                values['name'] = self.env['ir.sequence'].next_by_code('mrp.production') or _('New')
        if not values.get('procurement_group_id'):
            procurement_group_vals = self._prepare_procurement_group_vals(values)
            values['procurement_group_id'] = self.env["procurement.group"].create(procurement_group_vals).id
        production = super(MrpProduction, self).create(values)
        (production.move_raw_ids | production.move_finished_ids).write({
            'group_id': production.procurement_group_id.id,
            'origin': production.name
        })
        production.move_raw_ids.write({'date': production.date_planned_start})
        production.move_finished_ids.write({'date': production.date_planned_finished})
        # Trigger SM & WO creation when importing a file
        if 'import_file' in self.env.context:
            production._onchange_move_raw()
            production._onchange_move_finished()
            production._onchange_workorder_ids()
        return production

    def unlink(self):
        if any(production.state == 'done' for production in self):
            raise UserError(_('Cannot delete a manufacturing order in done state.'))
        self.action_cancel()
        not_cancel = self.filtered(lambda m: m.state != 'cancel')
        if not_cancel:
            productions_name = ', '.join([prod.display_name for prod in not_cancel])
            raise UserError(_('%s cannot be deleted. Try to cancel them before.', productions_name))

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

    def action_toggle_is_locked(self):
        self.ensure_one()
        self.is_locked = not self.is_locked
        return True

    def _create_workorder(self):
        for production in self:
            if not production.bom_id:
                continue
            workorders_values = []

            product_qty = production.product_uom_id._compute_quantity(production.product_qty, production.bom_id.product_uom_id)
            exploded_boms, dummy = production.bom_id.explode(production.product_id, product_qty / production.bom_id.product_qty, picking_type=production.bom_id.picking_type_id)

            for bom, bom_data in exploded_boms:
                # If the operations of the parent BoM and phantom BoM are the same, don't recreate work orders.
                if not (bom.operation_ids and (not bom_data['parent_line'] or bom_data['parent_line'].bom_id.operation_ids != bom.operation_ids)):
                    continue
                for operation in bom.operation_ids:
                    workorders_values += [{
                        'name': operation.name,
                        'production_id': production.id,
                        'workcenter_id': operation.workcenter_id.id,
                        'product_uom_id': production.product_uom_id.id,
                        'operation_id': operation.id,
                        'state': 'pending',
                        'consumption': production.consumption,
                    }]
            production.workorder_ids = [(5, 0)] + [(0, 0, value) for value in workorders_values]
            for workorder in production.workorder_ids:
                workorder.duration_expected = workorder._get_duration_expected()

    def _get_move_finished_values(self, product_id, product_uom_qty, product_uom, operation_id=False, byproduct_id=False):
        group_orders = self.procurement_group_id.mrp_production_ids
        move_dest_ids = self.move_dest_ids
        if len(group_orders) > 1:
            move_dest_ids |= group_orders[0].move_finished_ids.filtered(lambda m: m.product_id == self.product_id).move_dest_ids
        date_planned_finished = self.date_planned_start + relativedelta(days=self.product_id.produce_delay)
        date_planned_finished = date_planned_finished + relativedelta(days=self.company_id.manufacturing_lead)
        if date_planned_finished == self.date_planned_start:
            date_planned_finished = date_planned_finished + relativedelta(hours=1)
        return {
            'product_id': product_id,
            'product_uom_qty': product_uom_qty,
            'product_uom': product_uom,
            'operation_id': operation_id,
            'byproduct_id': byproduct_id,
            'name': self.name,
            'date': date_planned_finished,
            'date_deadline': self.date_deadline,
            'picking_type_id': self.picking_type_id.id,
            'location_id': self.product_id.with_company(self.company_id).property_stock_production.id,
            'location_dest_id': self.location_dest_id.id,
            'company_id': self.company_id.id,
            'production_id': self.id,
            'warehouse_id': self.location_dest_id.get_warehouse().id,
            'origin': self.name,
            'group_id': self.procurement_group_id.id,
            'propagate_cancel': self.propagate_cancel,
            'move_dest_ids': [(4, x.id) for x in self.move_dest_ids if not byproduct_id],
        }

    def _get_moves_finished_values(self):
        moves = []
        for production in self:
            if production.product_id in production.bom_id.byproduct_ids.mapped('product_id'):
                raise UserError(_("You cannot have %s  as the finished product and in the Byproducts", self.product_id.name))
            moves.append(production._get_move_finished_values(production.product_id.id, production.product_qty, production.product_uom_id.id))
            for byproduct in production.bom_id.byproduct_ids:
                product_uom_factor = production.product_uom_id._compute_quantity(production.product_qty, production.bom_id.product_uom_id)
                qty = byproduct.product_qty * (product_uom_factor / production.bom_id.product_qty)
                moves.append(production._get_move_finished_values(
                    byproduct.product_id.id, qty, byproduct.product_uom_id.id,
                    byproduct.operation_id.id, byproduct.id))
        return moves

    def _create_update_move_finished(self):
        """ This is a helper function to support complexity of onchange logic for MOs.
        It is important that the special *2Many commands used here remain as long as function
        is used within onchanges.
        """
        # keep manual entries
        list_move_finished = [(4, move.id) for move in self.move_finished_ids.filtered(
            lambda m: not m.byproduct_id and m.product_id != self.product_id)]
        list_move_finished = []
        moves_finished_values = self._get_moves_finished_values()
        moves_byproduct_dict = {move.byproduct_id.id: move for move in self.move_finished_ids.filtered(lambda m: m.byproduct_id)}
        move_finished = self.move_finished_ids.filtered(lambda m: m.product_id == self.product_id)
        for move_finished_values in moves_finished_values:
            if move_finished_values.get('byproduct_id') in moves_byproduct_dict:
                # update existing entries
                list_move_finished += [(1, moves_byproduct_dict[move_finished_values['byproduct_id']].id, move_finished_values)]
            elif move_finished_values.get('product_id') == self.product_id.id and move_finished:
                list_move_finished += [(1, move_finished.id, move_finished_values)]
            else:
                # add new entries
                list_move_finished += [(0, 0, move_finished_values)]
        self.move_finished_ids = list_move_finished

    def _get_moves_raw_values(self):
        moves = []
        for production in self:
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
        source_location = self.location_src_id
        data = {
            'sequence': bom_line.sequence if bom_line else 10,
            'name': self.name,
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
            'origin': self.name,
            'state': 'draft',
            'warehouse_id': source_location.get_warehouse().id,
            'group_id': self.procurement_group_id.id,
            'propagate_cancel': self.propagate_cancel,
        }
        return data

    def _set_qty_producing(self):
        if self.product_id.tracking == 'serial':
            qty_producing_uom = self.product_uom_id._compute_quantity(self.qty_producing, self.product_id.uom_id, rounding_method='HALF-UP')
            if qty_producing_uom != 1:
                self.qty_producing = self.product_id.uom_id._compute_quantity(1, self.product_uom_id, rounding_method='HALF-UP')

        for move in (self.move_raw_ids | self.move_finished_ids.filtered(lambda m: m.product_id != self.product_id)):
            if move._should_bypass_set_qty_producing() or not move.product_uom:
                continue
            new_qty = float_round((self.qty_producing - self.qty_produced) * move.unit_factor, precision_rounding=move.product_uom.rounding)
            move.move_line_ids.filtered(lambda ml: ml.state not in ('done', 'cancel')).qty_done = 0
            move.move_line_ids = move._set_quantity_done_prepare_vals(new_qty)

    def _update_raw_moves(self, factor):
        self.ensure_one()
        update_info = []
        move_to_unlink = self.env['stock.move']
        for move in self.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
            old_qty = move.product_uom_qty
            new_qty = old_qty * factor
            if new_qty > 0:
                move.write({'product_uom_qty': new_qty})
                move._action_assign()
                update_info.append((move, old_qty, new_qty))
            else:
                if move.quantity_done > 0:
                    raise UserError(_('Lines need to be deleted, but can not as you still have some quantities to consume in them. '))
                move._action_cancel()
                move_to_unlink |= move
        move_to_unlink.unlink()
        return update_info

    def _get_ready_to_produce_state(self):
        """ returns 'assigned' if enough components are reserved in order to complete
        the first operation of the bom. If not returns 'waiting'
        """
        self.ensure_one()
        first_operation = self.bom_id.operation_ids[0]
        if len(self.bom_id.operation_ids) == 1:
            moves_in_first_operation = self.move_raw_ids
        else:
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
            additional_moves.write({
                'group_id': production.procurement_group_id.id,
            })
            additional_moves._adjust_procure_method()
            moves_to_confirm |= additional_moves
            additional_byproducts = production.move_finished_ids.filtered(
                lambda move: move.state == 'draft'
            )
            moves_to_confirm |= additional_byproducts

        if moves_to_confirm:
            moves_to_confirm._action_confirm()
            # run scheduler for moves forecasted to not have enough in stock
            moves_to_confirm._trigger_scheduler()

        self.workorder_ids.filtered(lambda w: w.state not in ['done', 'cancel'])._action_confirm()

    def _get_children(self):
        self.ensure_one()
        procurement_moves = self.procurement_group_id.stock_move_ids
        child_moves = procurement_moves.move_orig_ids
        return (procurement_moves | child_moves).created_production_id.procurement_group_id.mrp_production_ids - self

    def _get_sources(self):
        self.ensure_one()
        dest_moves = self.procurement_group_id.mrp_production_ids.move_dest_ids
        parent_moves = self.procurement_group_id.stock_move_ids.move_dest_ids
        return (dest_moves | parent_moves).group_id.mrp_production_ids - self

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
        self.lot_producing_id = self.env['stock.production.lot'].create({
            'product_id': self.product_id.id,
            'company_id': self.company_id.id
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
            if not production.move_raw_ids:
                raise UserError(_("Add some materials to consume before marking this MO as to do."))
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
            (production.move_raw_ids | production.move_finished_ids)._action_confirm()
            production.workorder_ids._action_confirm()

        # run scheduler for moves forecasted to not have enough in stock
        self.move_raw_ids._trigger_scheduler()
        return True

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

        :param replan: If it is a replan, only ready and pending workorder will be take in account
        :type replan: bool.
        """
        self.ensure_one()

        if not self.workorder_ids:
            return
        # Schedule all work orders (new ones and those already created)
        qty_to_produce = max(self.product_qty - self.qty_produced, 0)
        qty_to_produce = self.product_uom_id._compute_quantity(qty_to_produce, self.product_id.uom_id)
        start_date = max(self.date_planned_start, datetime.datetime.now())
        if replan:
            workorder_ids = self.workorder_ids.filtered(lambda wo: wo.state in ['ready', 'pending'])
            # We plan the manufacturing order according to its `date_planned_start`, but if
            # `date_planned_start` is in the past, we plan it as soon as possible.
            workorder_ids.leave_id.unlink()
        else:
            workorder_ids = self.workorder_ids.filtered(lambda wo: not wo.date_planned_start)
        for workorder in workorder_ids:
            workcenters = workorder.workcenter_id | workorder.workcenter_id.alternative_workcenter_ids

            best_finished_date = datetime.datetime.max
            vals = {}
            for workcenter in workcenters:
                # compute theoretical duration
                if workorder.workcenter_id == workcenter:
                    duration_expected = workorder.duration_expected
                else:
                    duration_expected = workorder._get_duration_expected(alternative_workcenter=workcenter)

                from_date, to_date = workcenter._get_first_available_slot(start_date, duration_expected)
                # If the workcenter is unavailable, try planning on the next one
                if not from_date:
                    continue
                # Check if this workcenter is better than the previous ones
                if to_date and to_date < best_finished_date:
                    best_start_date = from_date
                    best_finished_date = to_date
                    best_workcenter = workcenter
                    vals = {
                        'workcenter_id': workcenter.id,
                        'duration_expected': duration_expected,
                    }

            # If none of the workcenter are available, raise
            if best_finished_date == datetime.datetime.max:
                raise UserError(_('Impossible to plan the workorder. Please check the workcenter availabilities.'))

            # Instantiate start_date for the next workorder planning
            if workorder.next_work_order_id:
                start_date = best_finished_date

            # Create leave on chosen workcenter calendar
            leave = self.env['resource.calendar.leaves'].create({
                'name': workorder.display_name,
                'calendar_id': best_workcenter.resource_calendar_id.id,
                'date_from': best_start_date,
                'date_to': best_finished_date,
                'resource_id': best_workcenter.resource_id.id,
                'time_type': 'other'
            })
            vals['leave_id'] = leave.id
            workorder.write(vals)
        self.with_context(force_date=True).write({
            'date_planned_start': self.workorder_ids[0].date_planned_start,
            'date_planned_finished': self.workorder_ids[-1].date_planned_finished
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
        ctx.update({'default_mrp_production_ids': self.ids, 'default_mrp_consumption_warning_line_ids': lines})
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
        self.workorder_ids.filtered(lambda x: x.state not in ['done', 'cancel']).action_cancel()
        if not self.move_raw_ids:
            self.state = 'cancel'
            return True
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
        for order in self:
            moves_not_to_do = order.move_raw_ids.filtered(lambda x: x.state == 'done')
            moves_to_do = order.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
            for move in moves_to_do.filtered(lambda m: m.product_qty == 0.0 and m.quantity_done > 0):
                move.product_uom_qty = move.quantity_done
            # MRP do not merge move, catch the result of _action_done in order
            # to get extra moves.
            moves_to_do = moves_to_do._action_done()
            moves_to_do = order.move_raw_ids.filtered(lambda x: x.state == 'done') - moves_not_to_do

            finish_moves = order.move_finished_ids.filtered(lambda m: m.product_id == order.product_id and m.state not in ('done', 'cancel'))
            # the finish move can already be completed by the workorder.
            if not finish_moves.quantity_done:
                finish_moves.quantity_done = float_round(order.qty_producing - order.qty_produced, precision_rounding=order.product_uom_id.rounding, rounding_method='HALF-UP')
                finish_moves.move_line_ids.lot_id = order.lot_producing_id
            order._cal_price(moves_to_do)

            moves_to_finish = order.move_finished_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
            moves_to_finish = moves_to_finish._action_done(cancel_backorder=cancel_backorder)
            order.action_assign()
            consume_move_lines = moves_to_do.mapped('move_line_ids')
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
        next_seq = max(self.procurement_group_id.mrp_production_ids.mapped("backorder_sequence"), default=1)
        return {
            'name': self._get_name_backorder(self.name, next_seq + 1),
            'backorder_sequence': next_seq + 1,
            'procurement_group_id': self.procurement_group_id.id,
            'move_raw_ids': None,
            'move_finished_ids': None,
            'product_qty': self._get_quantity_to_backorder(),
            'lot_producing_id': False,
            'origin': self.origin
        }

    def _generate_backorder_productions(self, close_mo=True):
        backorders = self.env['mrp.production']
        for production in self:
            if production.backorder_sequence == 0:  # Activate backorder naming
                production.backorder_sequence = 1
            production.name = self._get_name_backorder(production.name, production.backorder_sequence)
            backorder_mo = production.copy(default=production._get_backorder_mo_vals())
            if close_mo:
                production.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel')).write({
                    'raw_material_production_id': backorder_mo.id,
                })
                production.move_finished_ids.filtered(lambda m: m.state not in ('done', 'cancel')).write({
                    'production_id': backorder_mo.id,
                })
            else:
                new_moves_vals = []
                for move in production.move_raw_ids | production.move_finished_ids:
                    if not move.additional:
                        qty_to_split = move.product_uom_qty - move.unit_factor * production.qty_producing
                        qty_to_split = move.product_uom._compute_quantity(qty_to_split, move.product_id.uom_id, rounding_method='HALF-UP')
                        move_vals = move._split(qty_to_split)
                        if not move_vals:
                            continue
                        if move.raw_material_production_id:
                            move_vals[0]['raw_material_production_id'] = backorder_mo.id
                        else:
                            move_vals[0]['production_id'] = backorder_mo.id
                        new_moves_vals.append(move_vals[0])
                new_moves = self.env['stock.move'].create(new_moves_vals)
            backorders |= backorder_mo
            first_wo = self.env['mrp.workorder']
            for old_wo, wo in zip(production.workorder_ids, backorder_mo.workorder_ids):
                wo.qty_produced = max(old_wo.qty_produced - old_wo.qty_producing, 0)
                if wo.product_tracking == 'serial':
                    wo.qty_producing = 1
                else:
                    wo.qty_producing = wo.qty_remaining
                if wo.qty_producing == 0:
                    wo.action_cancel()
                if not first_wo and wo.state != 'cancel':
                    first_wo = wo
            first_wo.state = 'ready'

            # We need to adapt `duration_expected` on both the original workorders and their
            # backordered workorders. To do that, we use the original `duration_expected` and the
            # ratio of the quantity really produced and the quantity to produce.
            ratio = production.qty_producing / production.product_qty
            for workorder in production.workorder_ids:
                workorder.duration_expected = workorder.duration_expected * ratio
            for workorder in backorder_mo.workorder_ids:
                workorder.duration_expected = workorder.duration_expected * (1 - ratio)

        # As we have split the moves before validating them, we need to 'remove' the excess reservation
        if not close_mo:
            self.move_raw_ids.filtered(lambda m: not m.additional)._do_unreserve()
            self.move_raw_ids.filtered(lambda m: not m.additional)._action_assign()
        # Confirm only productions with remaining components
        backorders.filtered(lambda mo: mo.move_raw_ids).action_confirm()
        backorders.filtered(lambda mo: mo.move_raw_ids).action_assign()

        # Remove the serial move line without reserved quantity. Post inventory will assigned all the non done moves
        # So those move lines are duplicated.
        backorders.move_raw_ids.move_line_ids.filtered(lambda ml: ml.product_id.tracking == 'serial' and ml.product_qty == 0).unlink()
        backorders.move_raw_ids._recompute_state()

        return backorders

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
            close_mo = False
        else:
            productions_not_to_backorder = self
            productions_to_backorder = self.env['mrp.production']
            close_mo = True

        self.workorder_ids.button_finish()

        backorders = productions_to_backorder._generate_backorder_productions(close_mo=close_mo)
        productions_not_to_backorder._post_inventory(cancel_backorder=True)
        productions_to_backorder._post_inventory(cancel_backorder=False)

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
            if not any(production.move_raw_ids.mapped('quantity_done')):
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
        return True

    def button_unreserve(self):
        self.ensure_one()
        self.do_unreserve()
        return True

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

    @api.model
    def get_empty_list_help(self, help):
        self = self.with_context(
            empty_list_help_document_name=_("manufacturing order"),
        )
        return super(MrpProduction, self).get_empty_list_help(help)

    def _log_downside_manufactured_quantity(self, moves_modification, cancel=False):

        def _keys_in_sorted(move):
            """ sort by picking and the responsible for the product the
            move.
            """
            return (move.picking_id.id, move.product_id.responsible_id.id)

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
            return self.env.ref('mrp.exception_on_mo')._render(values=values)

        documents = self.env['stock.picking']._log_activity_get_documents(moves_modification, 'move_dest_ids', 'DOWN', _keys_in_sorted, _keys_in_groupby)
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
            return self.env.ref('mrp.exception_on_mo')._render(values=values)

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
