# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from datetime import datetime, timedelta
import babel

from odoo.addons.website.controllers.backend import WebsiteBackend
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class WebsiteSaleBackend(WebsiteBackend):

    @http.route()
    def fetch_dashboard_data(self, date_from, date_to):

        results = super(WebsiteSaleBackend, self).fetch_dashboard_data(date_from, date_to)
        results['groups']['sale_salesman'] = request.env['res.users'].has_group('sales_team.group_sale_salesman')
        if not results['groups']['sale_salesman']:
            return results

        date_from = datetime.strptime(date_from, DEFAULT_SERVER_DATE_FORMAT)
        date_to = datetime.strptime(date_to, DEFAULT_SERVER_DATE_FORMAT)

        # Best seller products
        product_lines = request.env['sale.order.line'].read_group(
            domain=[
                ('product_id.website_published', '=', True),
                ('order_id.state', 'in', ['sent', 'sale', 'done']),
                ('order_id.team_id.website_ids', '!=', False),
                ('order_id.date_order', '>=', date_from.strftime(DEFAULT_SERVER_DATE_FORMAT)),
                ('order_id.date_order', '<=', date_to.strftime(DEFAULT_SERVER_DATE_FORMAT))],
            fields=['product_id', 'product_uom_qty', 'price_total'],
            groupby='product_id', orderby='product_uom_qty desc', limit=5)

        best_sellers = []
        for product_line in product_lines:
            product_id = request.env['product.product'].browse(product_line['product_id'][0])
            best_sellers.append({
                'id': product_id.id,
                'name': product_id.name,
                'qty': product_line['product_uom_qty'],
                'sales': product_line['price_total'],
            })

        # Graphes computation
        sales_domain = [
            ('team_id.website_ids', '!=', False),
            ('state', 'in', ['sent', 'sale', 'done']),
        ]
        sales_graph = self._compute_sale_graph(date_from, date_to, sales_domain)
        previous_sales_graph = self._compute_sale_graph(date_from - timedelta(days=(date_to - date_from).days), date_from, sales_domain, previous=True)

        results['dashboards']['sales'] = {
            'graph': [
                {
                    'values': sales_graph,
                    'key': _('Sales'),
                },
                {
                    'values': previous_sales_graph,
                    'key': _('Previous Sales'),
                },
            ],
            'best_sellers': best_sellers,
        }

        return results

    def _compute_sale_graph(self, date_from, date_to, sales_domain, previous=False):

        days_between = (date_to - date_from).days
        date_list = [(date_from + timedelta(days=x)) for x in range(0, days_between + 1)]

        daily_sales = request.env['sale.order'].read_group(
            domain=sales_domain + [
                ('date_order', '>=', date_from.strftime(DEFAULT_SERVER_DATE_FORMAT)),
                ('date_order', '<=', date_to.strftime(DEFAULT_SERVER_DATE_FORMAT))],
            fields=['date_order', 'amount_total'],
            groupby='date_order:day')

        daily_sales_dict = {p['date_order:day']: p['amount_total'] for p in daily_sales}

        sales_graph = [{
            '0': d.strftime(DEFAULT_SERVER_DATE_FORMAT) if not previous else (d + timedelta(days=days_between)).strftime(DEFAULT_SERVER_DATE_FORMAT),
            # Respect read_group format in models.py
            '1': daily_sales_dict.get(babel.dates.format_date(d, format='dd MMM yyyy', locale=request.env.context.get('lang', 'en_US')), 0)
        } for d in date_list]

        return sales_graph
