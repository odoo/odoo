# Part of Odoo. See LICENSE file for full copyright and licensing details.

import babel.dates
from json import dumps
from datetime import datetime, time
from dateutil.relativedelta import relativedelta


from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.fields import Domain
from odoo.tools.date_utils import get_month, subtract
from odoo.tools.float_utils import float_round
from odoo.tools.misc import get_lang, format_date


class StockReplenishmentInfo(models.TransientModel):
    _name = 'stock.replenishment.info'
    _description = 'Stock supplier replenishment information'
    _rec_name = 'orderpoint_id'

    orderpoint_id = fields.Many2one('stock.warehouse.orderpoint')
    product_id = fields.Many2one('product.product', related='orderpoint_id.product_id')
    product_uom_name = fields.Char(related='orderpoint_id.product_uom_name')
    product_min_qty = fields.Float('Min', related='orderpoint_id.product_min_qty', readonly=False, related_sudo=False, required=True)
    product_max_qty = fields.Float('Max', related='orderpoint_id.product_max_qty', readonly=False, related_sudo=False, required=True)
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
        ],
        default='one_month',
        string='Based on',
        help="Estimate the sales volume for the period based on past period or order the forecasted quantity for that period.",
        required=True
    )
    percent_factor = fields.Integer(default=100, required=True)

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
            intermediary_date = fields.Date.today()
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
            _, lead_days_description = replenishment_report._get_lead_days_and_description()
            if lead_days_description:
                lead_days_description = _format_description(lead_days_description)
            replenishment_report.json_lead_days = dumps({
                'lead_horizon_date': format_date(self.env, replenishment_report.orderpoint_id.lead_horizon_date),
                'lead_days_description': lead_days_description,
                'today': format_date(self.env, fields.Date.today()),
                'trigger': orderpoint.trigger,
                'qty_forecast': self.env['ir.qweb.field.float'].value_to_html(orderpoint.qty_forecast, {'decimal_precision': 'Product Unit'}),
                'qty_to_order': self.env['ir.qweb.field.float'].value_to_html(orderpoint.qty_to_order, {'decimal_precision': 'Product Unit'}),
                'product_min_qty': self.env['ir.qweb.field.float'].value_to_html(orderpoint.product_min_qty, {'decimal_precision': 'Product Unit'}),
                'product_max_qty': self.env['ir.qweb.field.float'].value_to_html(orderpoint.product_max_qty, {'decimal_precision': 'Product Unit'}),
                'product_uom_name': orderpoint.product_uom_name,
                'virtual': orderpoint.trigger == 'manual' and orderpoint.create_uid.id == SUPERUSER_ID,
            })

    def _get_period_of_time(self):
        self.ensure_one()
        today = fields.Datetime.now()
        start_date = limit_date = today
        if self.based_on == 'one_week':
            start_date = start_date - relativedelta(weeks=1)
        elif self.based_on == 'one_month':
            start_date = start_date - relativedelta(months=1)
        elif self.based_on == 'three_months':
            start_date = start_date - relativedelta(months=3)
        elif self.based_on == 'one_year':
            start_date = start_date - relativedelta(years=1)
        else:  # Relative period of time.
            start_date = datetime(year=today.year - 1, month=today.month, day=1)
            if self.based_on == 'last_year_2':
                start_date += relativedelta(months=1)
            elif self.based_on == 'last_year_3':
                start_date += relativedelta(months=2)
            if self.based_on == 'last_year_quarter':
                limit_date = start_date + relativedelta(months=3)
            else:
                limit_date = start_date + relativedelta(months=1)
        return start_date, limit_date

    def _prepare_graph_data(self, daily_demand=0):
        self.ensure_one()
        if not daily_demand:
            ordering_period = 0
            x_axis_vals = ['', ' ']
            curve_line_vals = []
        else:
            qty_diff = self.product_max_qty - self.product_min_qty or 1
            ordering_period = max(1, int(qty_diff / daily_demand))
            x_axis_vals = ['']
            curve_line_vals = [{'x': '', 'y': self.product_max_qty}]
            for i in range(1, 4):
                date_string = _("In %s day(s)", int(i * ordering_period))
                x_axis_vals.append(date_string)
                curve_line_vals.append({'x': date_string, 'y': self.product_min_qty})
                curve_line_vals.append({'x': date_string, 'y': self.product_max_qty})
            curve_line_vals.pop()   # we pop the last value since it would result in an ascending line that we don't need

        max_line_vals = [{'x': date, 'y': self.product_max_qty} for date in x_axis_vals]
        min_line_vals = [{'x': date, 'y': self.product_min_qty} for date in x_axis_vals]
        graph_data = {
            'x_axis_vals': x_axis_vals,
            'max_line_vals': max_line_vals,
            'min_line_vals': min_line_vals,
            'curve_line_vals': curve_line_vals,
        }
        return ordering_period, graph_data

    @api.depends('orderpoint_id', 'based_on', 'percent_factor', 'product_min_qty', 'product_max_qty')
    def _compute_json_replenishment_graph(self):
        for replenishment_report in self:
            if not replenishment_report.product_id or not replenishment_report.orderpoint_id.location_id:
                continue
            lead_days, _ = replenishment_report._get_lead_days_and_description()
            date_from, date_to = replenishment_report._get_period_of_time()
            domain = Domain.AND([
                [('product_id', '=', replenishment_report.product_id.id)],
                [('date', '>=', date_from)],
                [('date', '<=', datetime.combine(date_to, time.max))],
                [('state', '=', 'done')],
                [('company_id', '=', replenishment_report.orderpoint_id.company_id.id)],
            ])
            quantity_out = self.env['stock.move']._read_group(
                Domain.AND([domain, [('location_dest_id.usage', '=', 'customer')]]),
                aggregates=['product_qty:sum'],
            )[0][0] or 0.0
            quantity_returned = self.env['stock.move']._read_group(
                Domain.AND([domain, [('location_id.usage', '=', 'customer')]]),
                aggregates=['product_qty:sum'],
            )[0][0] or 0.0

            if replenishment_report.product_max_qty < replenishment_report.product_min_qty:
                replenishment_report.product_max_qty = replenishment_report.product_min_qty
            average_stock = replenishment_report.product_min_qty + ((replenishment_report.product_max_qty - replenishment_report.product_min_qty) / 2)
            lead_time = lead_days.get('total_delay', 0)
            daily_demand = ((quantity_out - quantity_returned) / (date_to - date_from).days) * (replenishment_report.percent_factor / 100)

            ordering_period, graph_data = replenishment_report._prepare_graph_data(daily_demand=daily_demand)
            replenishment_report.json_replenishment_graph = dumps({
                'product_uom_name': replenishment_report.product_uom_name,
                'product_max_qty': replenishment_report.product_max_qty,
                'product_min_qty': replenishment_report.product_min_qty,
                'qty_on_hand': replenishment_report.orderpoint_id.qty_on_hand,
                'lead_time': lead_time,
                'daily_demand': float_round(daily_demand, precision_rounding=replenishment_report.product_id.uom_id.rounding),
                'average_stock': float_round(average_stock, precision_rounding=replenishment_report.product_id.uom_id.rounding),
                'ordering_period': float_round(ordering_period, precision_rounding=1),
                'x_axis_vals': graph_data["x_axis_vals"],
                'max_line_vals': graph_data["max_line_vals"],
                'min_line_vals': graph_data["min_line_vals"],
                'curve_line_vals': graph_data["curve_line_vals"],
            })


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

    @api.depends('replenishment_info_id')
    def _compute_lead_time(self):
        for record in self:
            rule = self.env['stock.rule']._get_rule(record.product_id, record.location_id, {
                'route_ids': record.route_id,
                'warehouse_id': record.warehouse_id,
            })
            delay = rule._get_lead_days(record.product_id)[0]['total_delay'] if rule else 0
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
