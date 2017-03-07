# -*- coding: utf-8 -*-

import babel

from datetime import datetime, timedelta, time

from odoo import fields, http, _
from odoo.addons.website.controllers.backend import WebsiteBackend
from odoo.http import request


class WebsiteSaleBackend(WebsiteBackend):

    @http.route()
    def fetch_dashboard_data(self, date_from, date_to):
        results = super(WebsiteSaleBackend, self).fetch_dashboard_data(date_from, date_to)

        sales_values = dict(
            graph=[],
            best_sellers=[],
            summary=dict(
                order_count=0, order_carts_count=0, order_unpaid_count=0,
                order_to_invoice_count=0, order_carts_abandoned_count=0,
                payment_to_capture_count=0, total_sold=0,
                order_per_day_ratio=0, order_sold_ratio=0, order_convertion_pctg=0,
            )
        )
        results['dashboards']['sales'] = sales_values

        results['groups']['sale_salesman'] = request.env['res.users'].has_group('sales_team.group_sale_salesman')
        if not results['groups']['sale_salesman']:
            return results

        date_date_from = fields.Date.from_string(date_from)
        date_date_to = fields.Date.from_string(date_to)
        date_diff_days = (date_date_to - date_date_from).days
        datetime_from = datetime.combine(date_date_from, time.min)
        datetime_to = datetime.combine(date_date_to, time.max)

        # Product-based computation
        report_product_lines = request.env['sale.report'].read_group(
            domain=[
                ('product_id.website_published', '=', True),
                ('team_id.team_type', '=', 'website'),
                ('state', 'in', ['sale', 'done']),
                ('date', '>=', date_from),
                ('date', '<=', date_to)],
            fields=['product_id', 'product_uom_qty', 'price_subtotal'],
            groupby='product_id', orderby='product_uom_qty desc', limit=5)
        for product_line in report_product_lines:
            product_id = request.env['product.product'].browse(product_line['product_id'][0])
            sales_values['best_sellers'].append({
                'id': product_id.id,
                'name': product_id.name,
                'qty': product_line['product_uom_qty'],
                'sales': product_line['price_subtotal'],
            })

        # Sale-based results computation
        sale_order_domain = [
            ('team_id', 'in', request.env['crm.team'].search([('team_type', '=', 'website')]).ids),
            ('date_order', '>=', fields.Datetime.to_string(datetime_from)),
            ('date_order', '<=', fields.Datetime.to_string(datetime_to))]
        so_group_data = request.env['sale.order'].read_group(sale_order_domain, fields=['state'], groupby='state')
        for res in so_group_data:
            if res.get('state') == 'sent':
                sales_values['summary']['order_unpaid_count'] += res['state_count']
            elif res.get('state') in ['sale', 'done']:
                sales_values['summary']['order_count'] += res['state_count']
            sales_values['summary']['order_carts_count'] += res['state_count']

        report_price_lines = request.env['sale.report'].read_group(
            domain=[
                ('team_id.team_type', '=', 'website'),
                ('state', 'in', ['sale', 'done']),
                ('date', '>=', date_from),
                ('date', '<=', date_to)],
            fields=['team_id', 'price_subtotal'],
            groupby=['team_id'],
        )
        sales_values['summary'].update(
            order_to_invoice_count=request.env['sale.order'].search_count(sale_order_domain + [
                ('state', 'in', ['sale', 'done']),
                ('order_line', '!=', False),
                ('partner_id', '!=', request.env.ref('base.public_partner').id),
                ('invoice_status', '=', 'to invoice'),
            ]),
            order_carts_abandoned_count=request.env['sale.order'].search_count(sale_order_domain + [
                ('state', '=', 'draft'),
                ('order_line', '!=', 'False'),
                ('date_order', '<=', fields.Datetime.to_string(datetime.now() - timedelta(hours=1))),
            ]),
            payment_to_capture_count=request.env['payment.transaction'].search_count([
                ('state', '=', 'authorized'),
                # that part perform a search on sale.order in order to comply with access rights as tx do not have any
                ('sale_order_id.id', 'in', request.env['sale.order'].search(sale_order_domain + [('state', '!=', 'cancel')]).ids),
            ]),
            total_sold=sum(price_line['price_subtotal'] for price_line in report_price_lines)
        )

        # Ratio computation
        sales_values['summary']['order_per_day_ratio'] = round(float(sales_values['summary']['order_count']) / date_diff_days, 2)
        sales_values['summary']['order_sold_ratio'] = round(float(sales_values['summary']['total_sold']) / sales_values['summary']['order_count'], 2) if sales_values['summary']['order_count'] else 0
        sales_values['summary']['order_convertion_pctg'] = 100.0 * sales_values['summary']['order_count'] / sales_values['summary']['order_carts_count'] if sales_values['summary']['order_carts_count'] else 0

        # Graphes computation
        if date_diff_days == 7:
            previous_sale_label = _('Previous Week')
        elif date_diff_days > 7 and date_diff_days <= 31:
            previous_sale_label = _('Previous Month')
        else:
            previous_sale_label = _('Previous Year')

        sales_domain = [
            ('team_id.team_type', '=', 'website'),
            ('state', 'in', ['sale', 'done']),
            ('date', '>=', date_from),
            ('date', '<=', date_to)
        ]
        sales_values['graph'] += [{
            'values': self._compute_sale_graph(date_date_from, date_date_to, sales_domain),
            'key': 'Untaxed Total',
        }, {
            'values': self._compute_sale_graph(date_date_from - timedelta(days=date_diff_days), date_date_from, sales_domain, previous=True),
            'key': previous_sale_label,
        }]

        return results

    def _compute_sale_graph(self, date_from, date_to, sales_domain, previous=False):

        days_between = (date_to - date_from).days
        date_list = [(date_from + timedelta(days=x)) for x in range(0, days_between + 1)]

        daily_sales = request.env['sale.report'].read_group(
            domain=sales_domain,
            fields=['date', 'price_subtotal'],
            groupby='date:day')

        daily_sales_dict = {p['date:day']: p['price_subtotal'] for p in daily_sales}

        sales_graph = [{
            '0': fields.Date.to_string(d) if not previous else fields.Date.to_string(d + timedelta(days=days_between)),
            # Respect read_group format in models.py
            '1': daily_sales_dict.get(babel.dates.format_date(d, format='dd MMM yyyy', locale=request.env.context.get('lang', 'en_US')), 0)
        } for d in date_list]

        return sales_graph
