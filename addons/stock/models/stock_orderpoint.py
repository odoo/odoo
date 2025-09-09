# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from pytz import timezone, UTC
from collections import defaultdict
from datetime import datetime, time
from dateutil import relativedelta
from psycopg2 import OperationalError

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.addons.stock.models.stock_rule import ProcurementException
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.modules.registry import Registry
from odoo.fields import Domain
from odoo.sql_db import BaseCursor
from odoo.tools import float_compare, float_is_zero, frozendict, split_every, format_date

_logger = logging.getLogger(__name__)


class StockWarehouseOrderpoint(models.Model):
    """ Defines Minimum stock rules. """
    _name = 'stock.warehouse.orderpoint'
    _description = "Minimum Inventory Rule"
    _check_company_auto = True
    _order = "location_id,company_id,id"

    name = fields.Char(
        'Name', copy=False, required=True, readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('stock.orderpoint'))
    trigger = fields.Selection([
        ('auto', 'Auto'), ('manual', 'Manual')], string='Trigger', default='auto', required=True)
    active = fields.Boolean(
        'Active', default=True,
        help="If the active field is set to False, it will allow you to hide the orderpoint without removing it.")
    snoozed_until = fields.Date('Snoozed', help="Hidden until next scheduler.")
    warehouse_id = fields.Many2one(
        'stock.warehouse', 'Warehouse',
        compute="_compute_warehouse_id", store=True, readonly=False, precompute=True,
        check_company=True, ondelete="cascade", required=True, index=True)
    location_id = fields.Many2one(
        'stock.location', 'Location', index=True,
        compute="_compute_location_id", store=True, readonly=False, precompute=True,
        ondelete="cascade", required=True, check_company=True)
    product_tmpl_id = fields.Many2one('product.template', related='product_id.product_tmpl_id')
    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=("[('product_tmpl_id', '=', context.get('active_id', False))] if context.get('active_model') == 'product.template' else"
            " [('id', '=', context.get('default_product_id', False))] if context.get('default_product_id') else"
            " [('is_storable', '=', True)]"),
        ondelete='cascade', required=True, check_company=True, index=True)
    product_category_id = fields.Many2one('product.category', name='Product Category', related='product_id.categ_id')
    product_uom = fields.Many2one(
        'uom.uom', 'Unit', related='product_id.uom_id')
    product_uom_name = fields.Char(string='Product unit of measure label', related='product_uom.display_name', readonly=True)
    product_min_qty = fields.Float(
        'Min Quantity', digits='Product Unit', required=True, default=0.0,
        help="The minimum Stock level that will trigger a replenishment.")
    product_max_qty = fields.Float(
        'Max Quantity', digits='Product Unit', required=True, default=0.0,
        compute='_compute_product_max_qty', readonly=False, store=True,
        help="Stock level to reach when replenishing.")
    allowed_replenishment_uom_ids = fields.Many2many('uom.uom', compute='_compute_allowed_replenishment_uom_ids')
    replenishment_uom_id = fields.Many2one(
        'uom.uom', 'Multiple',
        domain="[('id', 'in', allowed_replenishment_uom_ids)]", help="The procurement quantity will be rounded up to a multiple of this unit/packaging. If it is not set, it is not rounded.")
    replenishment_uom_id_placeholder = fields.Char(compute='_compute_replenishment_uom_id_placeholder')
    company_id = fields.Many2one(
        'res.company', 'Company', required=True, index=True,
        default=lambda self: self.env.company)
    allowed_location_ids = fields.One2many(comodel_name='stock.location', compute='_compute_allowed_location_ids')

    rule_ids = fields.Many2many('stock.rule', string='Rules used', compute='_compute_rules')
    lead_horizon_date = fields.Date(compute='_compute_lead_days')
    lead_days = fields.Float(compute='_compute_lead_days')
    route_id = fields.Many2one(
        'stock.route', string='Route',
        domain="['|', ('product_selectable', '=', True), ('rule_ids.action', 'in', ['buy', 'manufacture'])]",
        inverse='_inverse_route_id')
    route_id_placeholder = fields.Char(compute='_compute_route_id_placeholder')
    effective_route_id = fields.Many2one(
        'stock.route', search='_search_effective_route_id', compute='_compute_effective_route_id',
        store=False, help='Either the route set directly or the one computed to be used by this replenishment'
    )
    qty_on_hand = fields.Float('On Hand', readonly=True, compute='_compute_qty', digits='Product Unit')
    qty_forecast = fields.Float('Forecast', readonly=True, compute='_compute_qty', digits='Product Unit')
    qty_to_order = fields.Float('To Order', compute='_compute_qty_to_order', inverse='_inverse_qty_to_order', search='_search_qty_to_order', digits='Product Unit')
    qty_to_order_computed = fields.Float('To Order Computed', store=True, compute='_compute_qty_to_order_computed', digits='Product Unit')
    qty_to_order_manual = fields.Float('To Order Manual', digits='Product Unit')

    days_to_order = fields.Float(compute='_compute_days_to_order', help="Numbers of days  in advance that replenishments demands are created.")

    unwanted_replenish = fields.Boolean('Unwanted Replenish', compute="_compute_unwanted_replenish")
    show_supply_warning = fields.Boolean(compute="_compute_show_supply_warning")
    deadline_date = fields.Date("Deadline", compute="_compute_deadline_date", store=True, readonly=True,
                                help="Date before which you should order to avoid falling below the minimum. If you "
                                     "have nothing to order while a deadline is found, it may be because a future "
                                     "arrival is expected after the minimum quantity is reached (potential stockout). "
                                     "Check the Forecast Report.")

    _product_location_check = models.Constraint(
        'unique (product_id, location_id, company_id)',
        'A replenishment rule already exists for this product on this location.',
    )

    @api.depends('warehouse_id')
    def _compute_allowed_location_ids(self):
        # We want to keep only the locations
        #  - strictly belonging to our warehouse
        #  - not belonging to any warehouses
        for orderpoint in self:
            loc_domain = Domain('usage', 'in', ('internal', 'view'))
            other_warehouses = self.env['stock.warehouse'].search([('id', '!=', orderpoint.warehouse_id.id)])
            for view_location_id in other_warehouses.mapped('view_location_id'):
                loc_domain &= ~Domain('id', 'child_of', view_location_id.id)
                loc_domain &= Domain('company_id', 'in', [False, orderpoint.company_id.id])
            orderpoint.allowed_location_ids = self.env['stock.location'].search(loc_domain)

    def _compute_show_supply_warning(self):
        for orderpoint in self:
            orderpoint.show_supply_warning = not orderpoint.rule_ids

    @api.depends('location_id', 'product_min_qty', 'route_id', 'product_id.route_ids', 'product_id.stock_move_ids.date',
                 'product_id.stock_move_ids.state', 'product_id.seller_ids', 'product_id.seller_ids.delay', 'company_id.horizon_days')
    def _compute_deadline_date(self):
        """ This function first checks if the qty_on_hand is less than the product_min_qty. If it is the case,
        the deadline_date is set to the current day. Afterwards if there are still orderpoints to compute,
        it retrieves all the outgoing and incoming moves until the lead_horizon_date and adds (or subtracts)
        them to the qty_on_hand. The first instance when the qty_on_hand dips below the product_min_qty is
        the deadline date. """
        self.fetch(['qty_on_hand'])
        critical_orderpoints = self.filtered(lambda o: o.qty_on_hand < o.product_min_qty)
        critical_orderpoints.deadline_date = fields.Date.today()
        orderpoints_to_compute = self - critical_orderpoints
        if not orderpoints_to_compute:
            return

        # We have to filter by company here in case of multi-company and because horizon_days is a company setting
        for company in orderpoints_to_compute.company_id:
            company_orderpoints = orderpoints_to_compute.filtered(lambda c: c.company_id == company)
            horizon_date = fields.Date.today() + relativedelta.relativedelta(days=company_orderpoints.get_horizon_days())
            _, domain_move_in, domain_move_out = company_orderpoints.product_id._get_domain_locations()
            domain_move_in = Domain.AND([
                [('product_id', 'in', company_orderpoints.product_id.ids)],
                [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))],
                domain_move_in,
                [('date', '<=', horizon_date)],
            ])
            domain_move_out = Domain.AND([
                [('product_id', '=', company_orderpoints.product_id.ids)],
                [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))],
                domain_move_out,
                [('date', '<=', horizon_date)],
            ])

            Move = self.env['stock.move'].with_context(active_test=False)
            incoming_moves_by_product_date = Move._read_group(domain_move_in, ['product_id', 'location_dest_id', 'date:day'], ['product_qty:sum'])
            outgoing_moves_by_product_date = Move._read_group(domain_move_out, ['product_id', 'location_id', 'date:day'], ['product_qty:sum'])

            moves_by_product_dict = {}
            for product, location, in_date, in_qty in incoming_moves_by_product_date:
                if not moves_by_product_dict.get((product.id, location.id)):
                    moves_by_product_dict[product.id, location.id] = defaultdict(float)
                moves_by_product_dict[product.id, location.id][in_date.date()] += in_qty
            for product, location, out_date, out_qty in outgoing_moves_by_product_date:
                if not moves_by_product_dict.get((product.id, location.id)):
                    moves_by_product_dict[product.id, location.id] = defaultdict(float)
                moves_by_product_dict[product.id, location.id][out_date.date()] -= out_qty

            for orderpoint in company_orderpoints:
                qty_on_hand_at_date = orderpoint.qty_on_hand
                tentative_deadline = horizon_date
                for move_date, move_qty in sorted(moves_by_product_dict.get((orderpoint.product_id.id, orderpoint.location_id.id), {}).items()):
                    qty_on_hand_at_date += move_qty
                    if qty_on_hand_at_date < orderpoint.product_min_qty:
                        tentative_deadline = move_date - relativedelta.relativedelta(days=orderpoint.lead_days)
                        break
                orderpoint.deadline_date = tentative_deadline if tentative_deadline < horizon_date else False

    @api.depends('rule_ids', 'product_id.seller_ids', 'product_id.seller_ids.delay', 'company_id.horizon_days')
    def _compute_lead_days(self):
        orderpoints_to_compute = self.filtered(lambda orderpoint: orderpoint.product_id and orderpoint.location_id)
        for orderpoint in orderpoints_to_compute.with_context(bypass_delay_description=True):
            values = orderpoint._get_lead_days_values()
            lead_days, dummy = orderpoint.rule_ids._get_lead_days(orderpoint.product_id, **values)
            orderpoint.lead_horizon_date = fields.Date.today() + relativedelta.relativedelta(days=lead_days['total_delay'] + lead_days['horizon_time'])
            orderpoint.lead_days = lead_days['total_delay']
        (self - orderpoints_to_compute).lead_horizon_date = False
        (self - orderpoints_to_compute).lead_days = 0

    @api.depends('route_id', 'product_id', 'location_id', 'company_id', 'warehouse_id', 'product_id.route_ids')
    def _compute_rules(self):
        orderpoints_to_compute = self.filtered(lambda orderpoint: orderpoint.product_id and orderpoint.location_id)
        # Small cache mapping (location_id, route_id, product_id.route_ids | product_id.categ_id.total_route_ids) -> stock.rule.
        # This reduces calls to _get_rules_from_location for products without routes and products with the same routes.
        rules_cache = {}
        for orderpoint in orderpoints_to_compute:
            cache_key = (orderpoint.location_id, orderpoint.route_id, orderpoint.product_id.route_ids | orderpoint.product_id.categ_id.total_route_ids)
            rule_ids = rules_cache.get(cache_key) or orderpoint.product_id._get_rules_from_location(
                orderpoint.location_id, route_ids=orderpoint.route_id
            )
            orderpoint.rule_ids = rule_ids
            rules_cache[cache_key] = rule_ids
        (self - orderpoints_to_compute).rule_ids = False

    @api.depends('product_min_qty')
    def _compute_product_max_qty(self):
        for orderpoint in self:
            if orderpoint.product_max_qty < orderpoint.product_min_qty or not orderpoint.product_max_qty:
                orderpoint.product_max_qty = orderpoint.product_min_qty

    @api.depends('route_id', 'product_id', 'product_id.seller_ids', 'product_id.seller_ids.product_uom_id')
    def _compute_allowed_replenishment_uom_ids(self):
        for orderpoint in self:
            orderpoint.allowed_replenishment_uom_ids = orderpoint.product_id.uom_ids
            if 'buy' in orderpoint.rule_ids.mapped('action'):
                orderpoint.allowed_replenishment_uom_ids += orderpoint.product_id.seller_ids.product_uom_id

    @api.depends('allowed_replenishment_uom_ids')
    def _compute_replenishment_uom_id_placeholder(self):
        for orderpoint in self:
            replenishment_alternative = orderpoint._get_replenishment_multiple_alternative(orderpoint.qty_to_order)
            orderpoint.replenishment_uom_id_placeholder = replenishment_alternative.display_name if replenishment_alternative else ''

    def _inverse_route_id(self):
        # Override this method to add custom behavior when route is set
        pass

    @api.depends('product_id', 'product_id.categ_id', 'product_id.route_ids', 'product_id.categ_id.route_ids', 'location_id')
    def _compute_route_id_placeholder(self):
        for orderpoint in self:
            default_route = orderpoint._get_default_route()
            orderpoint.route_id_placeholder = default_route.display_name if default_route else ''

    @api.depends('route_id', 'product_id', 'product_id.categ_id', 'product_id.route_ids', 'product_id.categ_id.route_ids', 'location_id')
    def _compute_effective_route_id(self):
        for orderpoint in self:
            orderpoint.effective_route_id = orderpoint.route_id if orderpoint.route_id else orderpoint._get_default_route()

    def _search_effective_route_id(self, operator, value):
        routes = self.env['stock.route'].search([('id', operator, value)])
        orderpoints = self.env['stock.warehouse.orderpoint'].search([]).filtered(
            lambda orderpoint: orderpoint.effective_route_id in routes
        )
        return [('id', 'in', orderpoints.ids)]

    @api.depends('route_id', 'product_id')
    def _compute_days_to_order(self):
        self.days_to_order = 0

    @api.constrains('product_min_qty', 'product_max_qty')
    def _check_min_max_qty(self):
        if any(orderpoint.product_min_qty > orderpoint.product_max_qty for orderpoint in self):
            raise ValidationError(_('The minimum quantity must be less than or equal to the maximum quantity.'))

    @api.depends('location_id', 'company_id')
    def _compute_warehouse_id(self):
        for orderpoint in self:
            if orderpoint.location_id.warehouse_id:
                orderpoint.warehouse_id = orderpoint.location_id.warehouse_id
            elif orderpoint.company_id:
                orderpoint.warehouse_id = orderpoint.env['stock.warehouse'].search([
                    ('company_id', '=', orderpoint.company_id.id)
                ], limit=1)
            if not orderpoint.warehouse_id:
                self.env['stock.warehouse']._warehouse_redirect_warning()

    @api.depends('warehouse_id', 'company_id')
    def _compute_location_id(self):
        """ Finds location id for changed warehouse. """
        for orderpoint in self:
            warehouse = orderpoint.warehouse_id
            if not warehouse:
                warehouse = orderpoint.env['stock.warehouse'].search([
                    ('company_id', '=', orderpoint.company_id.id)
                ], limit=1)
            orderpoint.location_id = warehouse.lot_stock_id.id

    @api.depends('product_id', 'qty_to_order', 'product_max_qty')
    def _compute_unwanted_replenish(self):
        for orderpoint in self:
            if not orderpoint.product_id or orderpoint.product_uom.is_zero(orderpoint.qty_to_order) or orderpoint.product_uom.compare(orderpoint.product_max_qty, 0) == -1:
                orderpoint.unwanted_replenish = False
            else:
                after_replenish_qty = orderpoint.product_id.with_context(company_id=orderpoint.company_id.id, location=orderpoint.location_id.id).virtual_available + orderpoint.qty_to_order
                orderpoint.unwanted_replenish = orderpoint.product_uom.compare(after_replenish_qty, orderpoint.product_max_qty) > 0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom = self.product_id.uom_id.id

    @api.model_create_multi
    def create(self, vals_list):
        if any(val.get('snoozed_until', False) and val.get('trigger', self.default_get(['trigger'])['trigger']) == 'auto' for val in vals_list):
            raise UserError(_("You can not create a snoozed orderpoint that is not manually triggered."))
        return super().create(vals_list)

    def write(self, vals):
        if 'company_id' in vals:
            for orderpoint in self:
                if orderpoint.company_id.id != vals['company_id']:
                    raise UserError(_("Changing the company of this record is forbidden at this point, you should rather archive it and create a new one."))
        if 'snoozed_until' in vals:
            if any(orderpoint.trigger == 'auto' for orderpoint in self):
                raise UserError(_("You can only snooze manual orderpoints. You should rather archive 'auto-trigger' orderpoints if you do not want them to be triggered."))
        return super().write(vals)

    def action_product_forecast_report(self):
        self.ensure_one()
        action = self.product_id.action_product_forecast_report()
        action['context'] = {
            'active_id': self.product_id.id,
            'active_model': 'product.product',
            'lead_horizon_date': format_date(self.env, self.lead_horizon_date),
            'qty_to_order': self._get_qty_to_order(),
        }
        warehouse = self.warehouse_id
        if warehouse:
            action['context']['warehouse_id'] = warehouse.id
        return action

    @api.model
    def action_open_orderpoints(self):
        return self._get_orderpoint_action()

    def action_stock_replenishment_info(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('stock.action_stock_replenishment_info')
        action['name'] = _(
            'Replenishment Information for %(product)s in %(warehouse)s',
            product=self.product_id.display_name,
            warehouse=self.warehouse_id.display_name,
        )
        res = self.env['stock.replenishment.info'].create({
            'orderpoint_id': self.id,
        })
        action['res_id'] = res.id
        return action

    def action_replenish(self, force_to_max=False):
        now = self.env.cr.now()
        if force_to_max:
            for orderpoint in self:
                orderpoint.qty_to_order = orderpoint._get_multiple_rounded_qty(orderpoint.product_max_qty - orderpoint.qty_forecast)
        try:
            self._procure_orderpoint_confirm(company_id=self.env.company)
        except UserError as e:
            if len(self) != 1:
                raise e
            raise RedirectWarning(e, {
                'name': self.product_id.display_name,
                'type': 'ir.actions.act_window',
                'res_model': 'product.product',
                'res_id': self.product_id.id,
                'views': [(self.env.ref('product.product_normal_form_view').id, 'form')],
            }, _('Edit Product'))
        notification = False
        if len(self) == 1:
            notification = self.with_context(written_after=now)._get_replenishment_order_notification()
        # Forced to call compute quantity because we don't have a link.
        self.action_remove_manual_qty_to_order()
        self._compute_qty_to_order()
        self.filtered(lambda o: o.create_uid.id == SUPERUSER_ID and o.qty_to_order <= 0.0 and o.trigger == 'manual').unlink()
        return notification

    def action_replenish_auto(self):
        self.trigger = 'auto'
        return self.action_replenish()

    @api.depends('product_id', 'location_id', 'product_id.stock_move_ids', 'product_id.stock_move_ids.state',
                 'product_id.stock_move_ids.date', 'product_id.stock_move_ids.product_uom_qty', 'product_id.seller_ids.delay')
    def _compute_qty(self):
        orderpoints_contexts = defaultdict(lambda: self.env['stock.warehouse.orderpoint'])
        for orderpoint in self:
            if not orderpoint.product_id or not orderpoint.location_id:
                orderpoint.qty_on_hand = False
                orderpoint.qty_forecast = False
                continue
            orderpoint_context = orderpoint._get_product_context()
            product_context = frozendict({**orderpoint_context})
            orderpoints_contexts[product_context] |= orderpoint
        for orderpoint_context, orderpoints_by_context in orderpoints_contexts.items():
            products_qty = {
                p['id']: p for p in orderpoints_by_context.product_id.with_context(orderpoint_context).read(['qty_available', 'virtual_available'])
            }
            products_qty_in_progress = orderpoints_by_context._quantity_in_progress()
            for orderpoint in orderpoints_by_context:
                orderpoint.qty_on_hand = products_qty[orderpoint.product_id.id]['qty_available']
                orderpoint.qty_forecast = products_qty[orderpoint.product_id.id]['virtual_available'] + products_qty_in_progress[orderpoint.id]

    @api.depends('qty_to_order_manual', 'qty_to_order_computed')
    def _compute_qty_to_order(self):
        for orderpoint in self:
            orderpoint.qty_to_order = orderpoint.qty_to_order_manual if orderpoint.qty_to_order_manual else orderpoint.qty_to_order_computed

    def _inverse_qty_to_order(self):
        for orderpoint in self:
            if orderpoint.trigger == 'auto':
                orderpoint.qty_to_order_manual = 0
            elif not orderpoint.qty_to_order_manual and not orderpoint.qty_to_order:
                orderpoint.qty_to_order = orderpoint.qty_to_order_computed
            elif orderpoint.qty_to_order != orderpoint.qty_to_order_computed:
                orderpoint.qty_to_order_manual = orderpoint.qty_to_order

    def _search_qty_to_order(self, operator, value):
        records = self.search_fetch([('qty_to_order_manual', 'in', [0, False])], ['qty_to_order_computed'])
        matched_ids = records.filtered_domain([('qty_to_order_computed', operator, value)]).ids
        return ['|',
                    ('qty_to_order_manual', operator, value),
                    ('id', 'in', matched_ids)
                ]

    @api.depends('replenishment_uom_id', 'product_min_qty', 'product_max_qty',
    'product_id', 'location_id', 'product_id.seller_ids.delay', 'company_id.horizon_days')
    def _compute_qty_to_order_computed(self):
        def to_compute(orderpoint):
            rounding = orderpoint.product_uom.rounding
            # The check is on purpose. We only want to consider the horizon days if the forecast is negative and
            # there is already something to resupply base on lead times.
            return (
                orderpoint.id
                and float_compare(orderpoint.qty_forecast, orderpoint.product_min_qty, precision_rounding=rounding) < 0
            )

        orderpoints = self.filtered(to_compute)
        qty_in_progress_by_orderpoint = orderpoints._quantity_in_progress()
        for orderpoint in orderpoints:
            orderpoint.qty_to_order_computed = orderpoint._get_qty_to_order(qty_in_progress_by_orderpoint=qty_in_progress_by_orderpoint)
        (self - orderpoints).qty_to_order_computed = False

    def _get_default_rule(self):
        self.ensure_one()
        return self.env['stock.rule']._get_rule(self.product_id, self.location_id, {
            'route_ids': self.route_id,
            'warehouse_id': self.warehouse_id,
        })

    def _get_default_route(self):
        self.ensure_one()
        rules_groups = self.env['stock.rule']._read_group([
            '|', ('route_id.product_selectable', '!=', False),
            ('route_id.product_categ_selectable', '!=', False),
            ('location_dest_id', 'in', self.location_id.ids),
            ('action', 'in', ['pull_push', 'pull']),
            ('route_id.active', '!=', False)
        ], ['location_dest_id', 'route_id'])
        for location_dest, route in rules_groups:
            if route in (self.product_id.route_ids | self.product_id.categ_id.route_ids) and self.location_id == location_dest:
                return route
        return self.env['stock.route']

    def _get_replenishment_multiple_alternative(self, qty_to_order):
        """
        This method is used to get the alternative replenishment_uom_id for the orderpoint if not set manually.
        To be overridden in relevant modules.
        """
        return False

    def _get_qty_to_order(self, qty_in_progress_by_orderpoint=None):
        self.ensure_one()
        qty_to_order = 0.0
        qty_in_progress_by_orderpoint = qty_in_progress_by_orderpoint or {}
        qty_in_progress = qty_in_progress_by_orderpoint.get(self.id)
        if qty_in_progress is None:
            qty_in_progress = self._quantity_in_progress()[self.id]
        rounding = self.product_uom.rounding
        # The check is on purpose. We only want to consider the horizon days if the forecast is negative and
        # there is already something to resupply base on lead times.
        if float_compare(self.qty_forecast, self.product_min_qty, precision_rounding=rounding) < 0:
            product_context = self._get_product_context()
            qty_forecast_with_visibility = self.product_id.with_context(product_context).read(['virtual_available'])[0]['virtual_available'] + qty_in_progress
            qty_to_order = max(self.product_min_qty, self.product_max_qty) - qty_forecast_with_visibility
            qty_to_order = self._get_multiple_rounded_qty(qty_to_order)
        return qty_to_order

    def _get_lead_days_values(self):
        self.ensure_one()
        return {
            'days_to_order': self.days_to_order,
        }

    def _get_product_context(self):
        """Used to call `virtual_available` when running an orderpoint."""
        self.ensure_one()
        return {
            'location': self.location_id.id,
            'to_date': datetime.combine(self.lead_horizon_date, time.max)
        }

    def _get_orderpoint_action(self):
        """Create manual orderpoints for missing product in each warehouses. It also removes
        orderpoints that have been replenish. In order to do it:
        - It uses the report.stock.quantity to find missing quantity per product/warehouse
        - It checks if orderpoint already exist to refill this location.
        - It checks if it exists other sources (e.g RFQ) tha refill the warehouse.
        - It creates the orderpoints for missing quantity that were not refill by an upper option.

        return replenish report ir.actions.act_window
        """
        def is_parent_path_in(resupply_loc, path_dict, record_loc):
            return record_loc and resupply_loc.parent_path in path_dict.get(record_loc, '')

        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_orderpoint_replenish")
        action['context'] = self.env.context
        # Search also with archived ones to avoid to trigger product_location_check SQL constraints later
        # It means that when there will be a archived orderpoint on a location + product, the replenishment
        # report won't take in account this location + product and it won't create any manual orderpoint
        # In master: the active field should be remove
        orderpoints = self.env['stock.warehouse.orderpoint'].with_context(active_test=False).search([])
        # Remove previous automatically created orderpoint that has been refilled.
        orderpoints_removed = orderpoints._unlink_processed_orderpoints()
        orderpoints = orderpoints - orderpoints_removed
        if self.env.context.get('force_orderpoint_recompute', False):
            orderpoints._compute_qty_to_order_computed()
            orderpoints._compute_deadline_date()
        to_refill = defaultdict(float)
        all_product_ids = self._get_orderpoint_products()
        all_replenish_location_ids = self._get_orderpoint_locations()
        ploc_per_day = defaultdict(set)
        # For each replenish location get products with negative virtual_available aka forecast

        Move = self.env['stock.move'].with_context(active_test=False)
        Quant = self.env['stock.quant'].with_context(active_test=False)
        domain_quant, domain_move_in_loc, domain_move_out_loc = all_product_ids._get_domain_locations_new(all_replenish_location_ids.ids)
        domain_state = Domain('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))
        domain_product = Domain('product_id', 'in', all_product_ids.ids)

        domain_quant = Domain.AND((domain_product, domain_quant))
        domain_move_in = Domain.AND((domain_product, domain_state, domain_move_in_loc))
        domain_move_out = Domain.AND((domain_product, domain_state, domain_move_out_loc))

        moves_in = defaultdict(list)
        for item in Move._read_group(domain_move_in, ['product_id', 'location_dest_id', 'location_final_id'], ['product_qty:sum']):
            moves_in[item[0]].append((item[1], item[2], item[3]))

        moves_out = defaultdict(list)
        for item in Move._read_group(domain_move_out, ['product_id', 'location_id'], ['product_qty:sum']):
            moves_out[item[0]].append((item[1], item[2]))

        quants = defaultdict(list)
        for item in Quant._read_group(domain_quant, ['product_id', 'location_id'], ['quantity:sum']):
            quants[item[0]].append((item[1], item[2]))

        path = {loc: loc.parent_path for loc in self.env['stock.location'].with_context(active_test=False).search([('id', 'child_of', all_replenish_location_ids.ids)])}
        for loc in all_replenish_location_ids:
            for product in all_product_ids:
                qty_available = sum(q[1] for q in quants.get(product, [(0, 0)]) if is_parent_path_in(loc, path, q[0]))
                incoming_qty = sum(m[2] for m in moves_in.get(product, [(0, 0, 0)]) if is_parent_path_in(loc, path, m[0]) or is_parent_path_in(loc, path, m[1]))
                outgoing_qty = sum(m[1] for m in moves_out.get(product, [(0, 0)]) if is_parent_path_in(loc, path, m[0]))
                if product.uom_id.compare(qty_available + incoming_qty - outgoing_qty, 0) < 0:
                    # group product by lead_days and location in order to read virtual_available
                    # in batch
                    rules = product._get_rules_from_location(loc)
                    lead_days = rules.with_context(bypass_delay_description=True)._get_lead_days(product)[0]
                    ploc_per_day[lead_days['total_delay'] + lead_days['horizon_time'], loc].add(product.id)

        # recompute virtual_available with lead days
        today = fields.Datetime.now().replace(hour=23, minute=59, second=59)
        product_ids = set()
        location_ids = set()
        for (days, loc), prod_ids in ploc_per_day.items():
            products = self.env['product.product'].browse(prod_ids)
            qties = products.with_context(
                location=loc.id,
                to_date=today + relativedelta.relativedelta(days=days)
            ).read(['virtual_available'])
            for (product, qty) in zip(products, qties):
                if product.uom_id.compare(qty['virtual_available'], 0) < 0:
                    to_refill[(qty['id'], loc.id)] = qty['virtual_available']
                    product_ids.add(qty['id'])
                    location_ids.add(loc.id)
            products.invalidate_recordset()
        if not to_refill:
            return action

        # Remove incoming quantity from other origin than moves (e.g RFQ)
        product_ids = list(product_ids)
        location_ids = list(location_ids)
        qty_by_product_loc = self.env['product.product'].browse(product_ids)._get_quantity_in_progress(location_ids=location_ids)[0]
        rounding = self.env['decimal.precision'].precision_get('Product Unit')
        # Group orderpoint by product-location
        orderpoint_by_product_location = self.env['stock.warehouse.orderpoint']._read_group(
            [('id', 'in', orderpoints.ids), ('product_id', 'in', product_ids)],
            ['product_id', 'location_id'],
            ['id:recordset'])
        orderpoint_by_product_location = {
            (product.id, location.id): orderpoint.qty_to_order
            for product, location, orderpoint in orderpoint_by_product_location
        }
        for (product, location), product_qty in to_refill.items():
            qty_in_progress = qty_by_product_loc.get((product, location)) or 0.0
            qty_in_progress += orderpoint_by_product_location.get((product, location), 0.0)
            # Add qty to order for other orderpoint under this location.
            if not qty_in_progress:
                continue
            to_refill[(product, location)] = product_qty + qty_in_progress
        to_refill = {k: v for k, v in to_refill.items() if float_compare(
            v, 0.0, precision_digits=rounding) < 0.0}

        # With archived ones to avoid `product_location_check` SQL constraints
        orderpoint_by_product_location = self.env['stock.warehouse.orderpoint'].with_context(active_test=False)._read_group(
            [('id', 'in', orderpoints.ids), ('product_id', 'in', product_ids)],
            ['product_id', 'location_id'],
            ['id:recordset'])
        orderpoint_by_product_location = {
            (product.id, location.id): orderpoint
            for product, location, orderpoint in orderpoint_by_product_location
        }

        orderpoint_values_list = []
        for (product, location_id), product_qty in to_refill.items():
            orderpoint = orderpoint_by_product_location.get((product, location_id))
            if orderpoint:
                orderpoint.qty_forecast += product_qty
            else:
                orderpoint_values = self.env['stock.warehouse.orderpoint']._get_orderpoint_values(product, location_id)
                location = self.env['stock.location'].browse(location_id)
                orderpoint_values.update({
                    'name': _('Replenishment Report'),
                    'warehouse_id': location.warehouse_id.id or self.env['stock.warehouse'].search([('company_id', '=', location.company_id.id)], limit=1).id,
                    'company_id': location.company_id.id,
                })
                orderpoint_values_list.append(orderpoint_values)

        orderpoints = self.env['stock.warehouse.orderpoint'].with_user(SUPERUSER_ID).create(orderpoint_values_list)
        return action

    def action_remove_manual_qty_to_order(self):
        self.qty_to_order_manual = 0

    @api.model
    def _get_orderpoint_values(self, product, location):
        return {
            'product_id': product,
            'location_id': location,
            'product_max_qty': 0.0,
            'product_min_qty': 0.0,
            'trigger': 'manual',
        }

    def _get_replenishment_order_notification(self):
        self.ensure_one()
        domain = Domain('orderpoint_id', 'in', self.ids)
        if self.env.context.get('written_after'):
            domain &= Domain('write_date', '>=', self.env.context.get('written_after'))
        move = self.env['stock.move'].search(domain, limit=1)
        if ((move.location_id.warehouse_id and move.location_id.warehouse_id != self.warehouse_id)
            or move.location_id.usage == 'transit') and move.picking_id:
            action = self.env.ref('stock.stock_picking_action_picking_type')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('The inter-warehouse transfers have been generated'),
                    'message': '%s',
                    'links': [{
                        'label': move.picking_id.name,
                        'url': f'/odoo/action-stock.stock_picking_action_picking_type/{move.picking_id.id}'
                    }],
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        return False

    def _quantity_in_progress(self):
        """Return Quantities that are not yet in virtual stock but should be deduced from orderpoint rule
        (example: purchases created from orderpoints)"""
        return dict(self.mapped(lambda x: (x.id, 0.0)))

    @api.autovacuum
    def _unlink_processed_orderpoints(self):
        domain = Domain([
            ('create_uid', '=', SUPERUSER_ID),
            ('trigger', '=', 'manual'),
        ])
        if self.ids:
            domain &= Domain('id', 'in', self.ids)
        manual_orderpoints = self.env['stock.warehouse.orderpoint'].with_context(active_test=False).search(domain)
        orderpoints_to_remove = manual_orderpoints.filtered(lambda o: o.qty_to_order <= 0.0)
        # Remove previous automatically created orderpoint that has been refilled.
        orderpoints_to_remove.unlink()
        return orderpoints_to_remove

    def _prepare_procurement_values(self, date=False):
        """ Prepare specific key for moves or other components that will be created from a stock rule
        comming from an orderpoint. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        date_deadline = date or fields.Date.today()
        dates_info = self.product_id._get_dates_info(date_deadline, self.location_id, route_ids=self.route_id)
        values = {
            'route_ids': self.route_id,
            'date_planned': dates_info['date_planned'],
            'date_order': dates_info['date_order'],
            'date_deadline': date or False,
            'warehouse_id': self.warehouse_id,
            'orderpoint_id': self,
        }
        reference = self.env.context.get('origins')
        if reference:
            values['reference_ids'] = self.env['stock.reference'].browse(reference.get(self.id))
        return values

    def _procure_orderpoint_confirm(self, use_new_cursor=False, company_id=None, raise_user_error=True):
        """ Create procurements based on orderpoints.
        :param bool use_new_cursor: if set, use a dedicated cursor and auto-commit after processing
            1000 orderpoints.
            This is appropriate for batch jobs only.
        """
        self = self.with_company(company_id)

        for orderpoints_batch_ids in split_every(1000, self.ids):
            if use_new_cursor:
                assert isinstance(self.env.cr, BaseCursor)
                cr = Registry(self.env.cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))
            try:
                orderpoints_batch = self.env['stock.warehouse.orderpoint'].browse(orderpoints_batch_ids)
                all_orderpoints_exceptions = []
                while orderpoints_batch:
                    procurements = []
                    for orderpoint in orderpoints_batch:
                        origins = orderpoint.env.context.get('origins', {}).get(orderpoint.id, False)
                        if origins:
                            origins = self.env['stock.reference'].browse(origins)
                            origin = '%s - %s' % (orderpoint.display_name, ','.join(origins.mapped('name')))
                        else:
                            origin = orderpoint.name
                        if orderpoint.product_uom.compare(orderpoint.qty_to_order, 0.0) == 1:
                            date = orderpoint._get_orderpoint_procurement_date()
                            global_horizon_days = orderpoint.get_horizon_days()
                            if global_horizon_days:
                                date -= relativedelta.relativedelta(days=int(global_horizon_days))
                            values = orderpoint._prepare_procurement_values(date=date)
                            procurements.append(self.env['stock.rule'].Procurement(
                                orderpoint.product_id, orderpoint.qty_to_order, orderpoint.product_uom,
                                orderpoint.location_id, orderpoint.name, origin,
                                orderpoint.company_id, values))

                    try:
                        with self.env.cr.savepoint():
                            self.env['stock.rule'].with_context(from_orderpoint=True).run(procurements, raise_user_error=raise_user_error)
                    except ProcurementException as errors:
                        orderpoints_exceptions = []
                        for procurement, error_msg in errors.procurement_exceptions:
                            orderpoints_exceptions += [(procurement.values.get('orderpoint_id'), error_msg)]
                        all_orderpoints_exceptions += orderpoints_exceptions
                        failed_orderpoints = self.env['stock.warehouse.orderpoint'].concat(*[o[0] for o in orderpoints_exceptions])
                        if not failed_orderpoints:
                            _logger.error('Unable to process orderpoints')
                            break
                        orderpoints_batch -= failed_orderpoints

                    except OperationalError:
                        if use_new_cursor:
                            cr.rollback()
                            continue
                        else:
                            raise
                    else:
                        orderpoints_batch._post_process_scheduler()
                        break

                # Log an activity on product template for failed orderpoints.
                for orderpoint, error_msg in all_orderpoints_exceptions:
                    existing_activity = self.env['mail.activity'].search([
                        ('res_id', '=', orderpoint.product_id.product_tmpl_id.id),
                        ('res_model_id', '=', self.env.ref('product.model_product_template').id),
                        ('note', '=', error_msg)])
                    if not existing_activity:
                        orderpoint.product_id.product_tmpl_id.sudo().activity_schedule(
                            'mail.mail_activity_data_warning',
                            note=error_msg,
                            user_id=orderpoint.product_id.responsible_id.id or SUPERUSER_ID,
                        )

            finally:
                if use_new_cursor:
                    try:
                        cr.commit()
                    finally:
                        cr.close()
                    _logger.info("A batch of %d orderpoints is processed and committed", len(orderpoints_batch_ids))

        return {}

    def _post_process_scheduler(self):
        return True

    def _get_orderpoint_procurement_date(self):
        return timezone(self.company_id.partner_id.tz or 'UTC').localize(datetime.combine(self.lead_horizon_date, time(12))).astimezone(UTC).replace(tzinfo=None)

    def _get_orderpoint_products(self):
        return self.env['product.product'].search([('is_storable', '=', True), ('stock_move_ids', '!=', False)])

    def _get_orderpoint_locations(self):
        return self.env['stock.location'].search([('replenish_location', '=', True)])

    def _get_multiple_rounded_qty(self, qty_to_order):
        replenishment_multiple = self.replenishment_uom_id or self._get_replenishment_multiple_alternative(qty_to_order)
        if replenishment_multiple and replenishment_multiple != self.product_id.uom_id:
            # Replace the UP by DOWN if we don't want to order more quantity than product_max_qty
            qty_to_order = self.product_id.uom_id._compute_quantity(qty_to_order, replenishment_multiple)
            qty_to_order = fields.Float.round(qty_to_order, precision_digits=0, rounding_method="UP")
            qty_to_order = replenishment_multiple._compute_quantity(qty_to_order, self.product_id.uom_id)
        return qty_to_order

    def get_horizon_days(self):
        """ Return the value for Horizon. This can be (in order of priority):
        - the value set in context in the replenishment view
        - the value set on the company of the all the records in self. There should be at most 1 company_id on self.
        - the value set on the company of the user if all else fail.
        """
        return self.env.context.get('global_horizon_days', (self.company_id or self.env.company).horizon_days)
