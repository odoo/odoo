# Part of Odoo. See LICENSE file for full copyright and licensing details.

from json import dumps
from dateutil.relativedelta import relativedelta


from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools.float_utils import float_round
from odoo.tools.misc import format_date


class StockReplenishmentInfo(models.TransientModel):
    _name = 'stock.replenishment.info'
    _description = 'Stock supplier replenishment information'
    _rec_name = 'orderpoint_id'

    orderpoint_id = fields.Many2one('stock.warehouse.orderpoint')
    product_id = fields.Many2one('product.product', related='orderpoint_id.product_id')
    product_uom_name = fields.Char(related='orderpoint_id.product_uom_name')
    product_min_qty = fields.Float('Min', related='orderpoint_id.product_min_qty', readonly=False, related_sudo=False, required=True)
    product_max_qty = fields.Float('Max', related='orderpoint_id.product_max_qty', readonly=False, related_sudo=False, required=True)
    daily_demand = fields.Float("Demand is", related='orderpoint_id.daily_demand', readonly=False, related_sudo=False, required=True)
    min_coverage = fields.Integer(
        compute='_compute_min_coverage', readonly=False,
        help="Days of demand covered by Minimum level:\n"
             "Should be ≥ Replenishment Time - Sales Availability Time to avoid stock-outs during replenishment time.\n"
             "Include extra days of safety to buffer unusual situations.\n\n"
             "Green if > Replenishment Time - Sales Availability Time\n"
             "Orange if = Replenishment Time - Sales Availability Time\n"
             "Red if < Replenishment Time - Sales Availability Time")
    replenish_frequency = fields.Integer(
        compute='_compute_replenish_frequency', readonly=False,
        help="Replenishment Frequency: choose how many days there are between replenishment requests to optimize the balance "
             "between your storage costs and order costs and calculate your Maximum level.")
    qty_to_order = fields.Float(related='orderpoint_id.qty_to_order')
    json_lead_days = fields.Char(compute='_compute_json_lead_days')
    json_replenishment_graph = fields.Char(compute='_compute_json_replenishment_graph')
    based_on = fields.Selection(
        selection=[
            ('one_week', "Last 7 days"),
            ('one_month', "Last 30 days"),
            ('three_months', "Last 3 months"),
            ('one_year', "Last 12 months"),
            ('last_year', "Same month last year"),
            ('last_year_2', "Next month last year"),
            ('last_year_3', "After next month last year"),
            ('last_year_quarter', "Last year quarter"),
            ('custom', "Custom Demand"),
        ],
        default='one_month',
        string='Based on',
        help="Estimate the daily average future demand volume based on past period or choose Custom Demand to enter manually average daily demand.",
        required=True,
        inverse='_inverse_based_on',
    )
    percent_factor = fields.Integer(default=100, required=True, inverse='_inverse_percent_factor')
    danger_level = fields.Char(compute='_compute_danger_level')

    warehouseinfo_ids = fields.One2many(related='orderpoint_id.warehouse_id.resupply_route_ids')
    wh_replenishment_option_ids = fields.One2many('stock.replenishment.option', 'replenishment_info_id', compute='_compute_wh_replenishment_options')

    @api.depends('orderpoint_id')
    def _compute_wh_replenishment_options(self):
        for replenishment_info in self:
            replenishment_info.wh_replenishment_option_ids = self.env['stock.replenishment.option'].create([
                {'product_id': replenishment_info.product_id.id, 'route_id': route_id.id, 'replenishment_info_id': replenishment_info.id}
                for route_id in replenishment_info.warehouseinfo_ids
            ]).sorted(lambda o: o.free_qty, reverse=True)

    def _get_lead_days_and_description(self):
        self.ensure_one()
        orderpoint = self.orderpoint_id
        orderpoints_values = orderpoint._get_lead_days_values()
        return orderpoint.rule_ids._get_lead_days(orderpoint.product_id, **orderpoints_values)

    @api.depends('orderpoint_id')
    def _compute_json_lead_days(self):
        def _format_description(description):
            formatted_description = []
            intermediary_date = fields.Date.context_today(self)
            for line in reversed(description):
                if isinstance(line[1], str):
                    formatted_description.append((line[0], line[1], False))
                else:
                    intermediary_date = intermediary_date + relativedelta(days=int(line[1]))
                    formatted_description.append((line[0], format_date(self.env, intermediary_date), True))
            return formatted_description

        self.json_lead_days = False
        for replenishment_report in self:
            if not replenishment_report.product_id or not replenishment_report.orderpoint_id.location_id:
                continue
            orderpoint = replenishment_report.orderpoint_id
            lead_days, lead_days_description = replenishment_report._get_lead_days_and_description()
            if lead_days_description:
                lead_days_description = _format_description(lead_days_description)
            replenishment_report.json_lead_days = dumps({
                'lead_horizon_date': format_date(self.env, replenishment_report.orderpoint_id.lead_horizon_date),
                'lead_time': lead_days.get('total_delay', 0),
                'lead_days_description': lead_days_description,
                'today': format_date(self.env, fields.Date.context_today(self)),
                'trigger': orderpoint.trigger,
                'qty_forecast': self.env['ir.qweb.field.float'].value_to_html(orderpoint.qty_forecast, {'decimal_precision': 'Product Unit'}),
                'qty_to_order': self.env['ir.qweb.field.float'].value_to_html(orderpoint.qty_to_order, {'decimal_precision': 'Product Unit'}),
                'product_min_qty': self.env['ir.qweb.field.float'].value_to_html(orderpoint.product_min_qty, {'decimal_precision': 'Product Unit'}),
                'product_max_qty': self.env['ir.qweb.field.float'].value_to_html(orderpoint.product_max_qty, {'decimal_precision': 'Product Unit'}),
                'product_uom_name': orderpoint.product_uom_name,
                'virtual': orderpoint.trigger == 'manual' and orderpoint.create_uid.id == SUPERUSER_ID,
            })

    def _inverse_based_on(self):
        for report in self:
            if report.orderpoint_id.min_max_based_on != report.based_on:
                report.orderpoint_id.min_max_based_on = report.based_on

    def _inverse_percent_factor(self):
        for report in self:
            if report.orderpoint_id.min_max_based_on_factor != report.percent_factor:
                report.orderpoint_id.min_max_based_on_factor = report.percent_factor

    @api.onchange('daily_demand')
    def _onchange_daily_demand(self):
        self.based_on = 'custom'
        old_coverage = self.min_coverage
        old_frequency = self.replenish_frequency
        self.product_min_qty = float_round(self.daily_demand * self.min_coverage, precision_rounding=1)
        self.product_max_qty = float_round(self.product_min_qty + (self.daily_demand * self.replenish_frequency), precision_rounding=1)
        self.min_coverage = old_coverage
        self.replenish_frequency = old_frequency

    @api.onchange('min_coverage')
    def _onchange_min_coverage(self):
        old_coverage = self.min_coverage
        old_frequency = self.replenish_frequency
        self.product_min_qty = float_round(self.daily_demand * self.min_coverage, precision_rounding=1)
        self.product_max_qty = float_round(self.product_min_qty + (self.daily_demand * self.replenish_frequency), precision_rounding=1)
        self.min_coverage = old_coverage
        self.replenish_frequency = old_frequency

    @api.onchange('replenish_frequency')
    def _onchange_replenish_frequency(self):
        old_frequency = self.replenish_frequency
        self.product_max_qty = float_round(self.product_min_qty + (self.daily_demand * self.replenish_frequency), precision_rounding=1)
        self.replenish_frequency = old_frequency

    @api.depends('product_min_qty')
    def _compute_min_coverage(self):
        for report in self:
            if report.daily_demand == 0:
                report.min_coverage = 0
            else:
                report.min_coverage = float_round(report.product_min_qty / report.daily_demand, precision_rounding=1)

    @api.depends('product_max_qty')
    def _compute_replenish_frequency(self):
        for report in self:
            if report.daily_demand == 0:
                report.replenish_frequency = 0
            else:
                qty_diff = report.product_max_qty - report.product_min_qty
                report.replenish_frequency = float_round(qty_diff / report.daily_demand, precision_rounding=1)

    @api.depends('min_coverage')
    def _compute_danger_level(self):
        for report in self:
            warning_days = report._get_warning_days()
            if report.min_coverage > warning_days:
                report.danger_level = 'success'
            elif report.min_coverage == warning_days:
                report.danger_level = 'warning'
            else:
                report.danger_level = 'danger'

    def _get_warning_days(self):
        self.ensure_one()
        lead_days, _ = self._get_lead_days_and_description()
        return lead_days.get('total_delay', 0)

    # TODO: remove json_replenishment_graph field
    def _compute_json_replenishment_graph(self):
        self.json_replenishment_graph = ''

    def get_daily_demand(self, period=None, ratio=None):
        self.ensure_one()
        return self.orderpoint_id._get_daily_demand(period=period, ratio=ratio)


class StockReplenishmentOption(models.TransientModel):
    _name = 'stock.replenishment.option'
    _description = 'Stock warehouse replenishment option'

    route_id = fields.Many2one('stock.route')
    product_id = fields.Many2one('product.product')
    replenishment_info_id = fields.Many2one('stock.replenishment.info')

    location_id = fields.Many2one('stock.location', related='warehouse_id.lot_stock_id')
    warehouse_id = fields.Many2one('stock.warehouse', related='route_id.supplier_wh_id')
    uom = fields.Char(related='product_id.uom_name')
    qty_to_order = fields.Float(related='replenishment_info_id.qty_to_order')

    free_qty = fields.Float(compute='_compute_free_qty')
    lead_time = fields.Char(compute='_compute_lead_time')

    warning_message = fields.Char(compute='_compute_warning_message')

    @api.depends('product_id', 'route_id')
    def _compute_free_qty(self):
        for record in self:
            record.free_qty = record.product_id.with_context(location=record.location_id.id).free_qty

    @api.depends('product_id', 'route_id', 'replenishment_info_id')
    def _compute_lead_time(self):
        for record in self:
            orderpoint = record.replenishment_info_id.orderpoint_id
            rules = record.product_id._get_rules_from_location(
                orderpoint.location_id, route_ids=record.route_id
            )
            delay = rules._get_lead_days(record.product_id, **orderpoint._get_lead_days_values())[0]['total_delay'] if rules else 0
            record.lead_time = _("%s days", delay)

    @api.depends('warehouse_id', 'free_qty', 'uom', 'qty_to_order')
    def _compute_warning_message(self):
        self.warning_message = ''
        for record in self:
            if record.free_qty < record.qty_to_order:
                record.warning_message = _(
                    '%(warehouse)s can only provide %(free_qty)s %(uom)s, while the quantity to order is %(qty_to_order)s %(uom)s.',
                    warehouse=record.warehouse_id.name,
                    free_qty=record.free_qty,
                    uom=record.uom,
                    qty_to_order=record.qty_to_order
                )

    def select_route(self):
        if self.free_qty < self.qty_to_order:
            return {
                "type": "ir.actions.act_window",
                "res_model": "stock.replenishment.option",
                "res_id": self.id,
                "views": [[self.env.ref('stock.replenishment_option_warning_view').id, "form"]],
                "target": "new",
                "name": _("Quantity available too low")
            }
        return self.order_all()

    def order_avbl(self):
        self.replenishment_info_id.orderpoint_id.route_id = self.route_id
        self.replenishment_info_id.orderpoint_id.qty_to_order = self.free_qty
        return {'type': 'ir.actions.act_window_close'}

    def order_all(self):
        self.replenishment_info_id.orderpoint_id.route_id = self.route_id
        return {'type': 'ir.actions.act_window_close'}
