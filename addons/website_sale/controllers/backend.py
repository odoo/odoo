# -*- coding: utf-8 -*-
from odoo import fields, http, _
from odoo.http import request
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta
from math import floor
import time
import operator
import babel

from odoo.addons.website.controllers.backend import WebsiteBackend


class WebsiteSaleBackend(WebsiteBackend):

    @http.route()
    def fetch_dashboard_data(self, date_from, date_to):

        vals = super(WebsiteSaleBackend, self).fetch_dashboard_data(date_from, date_to)
        sale_salesman = request.env['res.users'].has_group('sales_team.group_sale_salesman')
        if not sale_salesman:
            return vals
        results = {
            'groups': vals.get('groups', {}),
            'currency': request.env.user.company_id.currency_id.id,
            'dashboards': vals.get('dashboards', {})
        }

        website_teams = request.env['crm.team'].search([]).filtered(lambda team: team.team_type == 'website')
        sale_order = request.env['sale.order'].search([('team_id', 'in', website_teams.ids), ('order_line', '!=', False)])

        if date_from:
            days_between = (fields.Date.from_string(date_to) - fields.Date.from_string(date_from)).days
        else:
            date_from = min(sale_order.mapped(lambda so: so.date_order))
            days_between = (fields.Date.from_string(date_to) - fields.Date.from_string(date_from)).days

        # Best seller products
        product_lines = request.env['sale.report'].read_group(
            domain=[
                ('product_id.website_published', '=', True),
                ('team_id', 'in', website_teams.ids),
                ('state', 'in', ['sale', 'done']),
                ('date', '>=', date_from),
                ('date', '<=', date_to)],
            fields=['product_id', 'product_uom_qty', 'price_subtotal'],
            groupby='product_id', orderby='product_uom_qty desc', limit=5)

        best_sellers = []
        for product_line in product_lines:
            product_id = request.env['product.product'].browse(product_line['product_id'][0])
            best_sellers.append({
                'id': product_id.id,
                'name': product_id.name,
                'qty': product_line['product_uom_qty'],
                'sales': product_line['price_subtotal'],
            })

        # Graphes computation
        sales_domain = [
            ('team_id', 'in', website_teams.ids),
            ('state', 'in', ['sale', 'done']),
            ('date', '>=', date_from),
            ('date', '<=', date_to)
        ]

        sales_graph = self._compute_sale_graph(fields.Date.from_string(date_from), days_between, sales_domain)
        previous_sales_graph = self._compute_sale_graph(fields.Date.from_string(date_from) - (timedelta(days=days_between)), days_between, sales_domain, previous=True)
        if days_between == 7:
            previous_sale_label = _('Previous Week')
        elif days_between > 7 and days_between <= 31:
            previous_sale_label = _('Previous Month')
        elif days_between > 31 and days_between <= 366:
            previous_sale_label = _('Previous Year')
        else:
            previous_sale_label = _('Previous Sales')

        # calculate the sale dashboard
        values = {
            'unpaid_orders': 0,
            'order_to_invoice': 0,
            'payment_to_capture': 0,
            'abandoned_carts': 0,
        }
        summary = {
            'sold': 0,
            'orders': 0,
            'carts': 0,
            'order_ratio': 0,
        }

        time_constraint = fields.Datetime.to_string(fields.datetime.now() - timedelta(hours=1))
        values['abandoned_carts'] = len(
            sale_order.filtered(lambda so: so.state == 'draft' and
            so.partner_id.id != request.env.ref('base.public_partner').id and
            so.date_order < time_constraint))
        values['order_to_invoice'] = len(sale_order.filtered(lambda so: so.state in ('sale', 'done') and so.invoice_status == 'to invoice'))
        summary['orders'] = len(sale_order.filtered(lambda so: so.state in ('sale', 'done') and so.date_order >= date_from and so.date_order <= fields.Datetime.to_string(fields.datetime.now())))
        summary['carts'] = len(sale_order.filtered(lambda so: so.date_order >= date_from and so.date_order <= fields.Datetime.to_string(fields.datetime.now())))
        summary['order_ratio'] = round(float(summary['orders'])/days_between, 2)
        values['unpaid_orders'] = len(sale_order.filtered(lambda so: so.state == 'sent'))

        summary['sold'] = sum(request.env['sale.report'].search([
                ('state', 'in', ['sale', 'done']),
                ('team_id', 'in', website_teams.ids),
                ('date', '>=', date_from),
                ('date', '<=', date_to)]).mapped('price_subtotal'))

        values['payment_to_capture'] = request.env['payment.transaction'].search_count([('state', '=','authorized'), ('sale_order_id.state', '!=', 'cancel')])

        if 'apps' in results['dashboards'] and len(results['dashboards']['apps']) > 0:
            count = (5 - len([val for val in values.values() if val > 0]))
            results['dashboards']['apps'] = results['dashboards']['apps'][:count]
        results['groups']['sale_salesman'] = sale_salesman
        results['dashboards']['sales'] = {
            'graph': [
                {
                    'values': sales_graph,
                    'key': 'Untaxed Total',
                },
                {
                    'values': previous_sales_graph,
                    'key': previous_sale_label,
                },
            ],
            'best_sellers': best_sellers,
            'values': values,
            'summary': summary,
        }

        return results

    def _compute_sale_graph(self, date_from, days_between, sales_domain, previous=False):
        date_list = [(date_from + timedelta(days=x)) for x in range(0, days_between + 1)]

        daily_sales = request.env['sale.report'].read_group(
            domain=sales_domain,
            fields=['date', 'price_subtotal'],
            groupby='date:day')

        daily_sales_dict = {p['date:day']: p['price_subtotal'] for p in daily_sales}
        sales_graph = [{
            '0': fields.Date.to_string(d) if not previous else (fields.Date.to_string(d + timedelta(days=days_between))),
            # Respect read_group format in models.py
            '1': daily_sales_dict.get(babel.dates.format_date(d, format='dd MMM yyyy', locale=request.env.context.get('lang', 'en_US')), 0)
        } for d in date_list]

        return sales_graph
