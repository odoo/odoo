# -*- coding: utf-8 -*-

import babel.dates

from datetime import datetime, timedelta, time

from odoo import fields, http, _
from odoo.addons.website.controllers.backend import WebsiteBackend
from odoo.http import request
from odoo.tools.misc import get_lang


class WebsiteSaleBackend(WebsiteBackend):

    @http.route()
    def fetch_dashboard_data(self, website_id, date_from, date_to):
        Website = request.env['website']
        current_website = website_id and Website.browse(website_id) or Website.get_current_website()

        results = super(WebsiteSaleBackend, self).fetch_dashboard_data(website_id, date_from, date_to)

        date_date_from = fields.Date.from_string(date_from)
        date_date_to = fields.Date.from_string(date_to)
        date_diff_days = (date_date_to - date_date_from).days
        datetime_from = datetime.combine(date_date_from, time.min)
        datetime_to = datetime.combine(date_date_to, time.max)

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

        results['dashboards']['sales']['utm_graph'] = self.fetch_utm_data(datetime_from, datetime_to)
        # Product-based computation
        sale_report_domain = [
            ('website_id', '=', current_website.id),
            ('state', '=', 'sale'),
            ('date', '>=', datetime_from),
            ('date', '<=', fields.Datetime.now())
        ]
        report_product_lines = request.env['sale.report']._read_group(
            domain=sale_report_domain,
            groupby=['product_tmpl_id'],
            aggregates=['product_uom_qty:sum', 'price_subtotal:sum'], order='product_uom_qty:sum desc', limit=5)
        for product_tmpl, product_uom_qty_sum, price_subtotal_sum in report_product_lines:
            sales_values['best_sellers'].append({
                'id': product_tmpl.id,
                'name': product_tmpl.name,
                'qty': product_uom_qty_sum,
                'sales': price_subtotal_sum,
            })

        # Sale-based results computation
        sale_order_domain = [
            ('website_id', '=', current_website.id),
            ('date_order', '>=', fields.Datetime.to_string(datetime_from)),
            ('date_order', '<=', fields.Datetime.to_string(datetime_to))]
        so_group_data = request.env['sale.order']._read_group(sale_order_domain, groupby=['state'], aggregates=['__count'])
        for state, count in so_group_data:
            if state == 'sent':
                sales_values['summary']['order_unpaid_count'] += count
            elif state == 'sale':
                sales_values['summary']['order_count'] += count
            sales_values['summary']['order_carts_count'] += count

        [price_subtotal] = request.env['sale.report']._read_group(
            domain=[
                ('website_id', '=', current_website.id),
                ('state', '=', 'sale'),
                ('date', '>=', datetime_from),
                ('date', '<=', datetime_to)],
            aggregates=['price_subtotal:sum'],
        )[0]
        sales_values['summary'].update(
            order_to_invoice_count=request.env['sale.order'].search_count(sale_order_domain + [
                ('state', '=', 'sale'),
                ('order_line', '!=', False),
                ('partner_id', '!=', request.env.ref('base.public_partner').id),
                ('invoice_status', '=', 'to invoice'),
            ]),
            order_carts_abandoned_count=request.env['sale.order'].search_count(sale_order_domain + [
                ('is_abandoned_cart', '=', True),
                ('cart_recovery_email_sent', '=', False)
            ]),
            payment_to_capture_count=request.env['payment.transaction'].search_count([
                ('state', '=', 'authorized'),
                # that part perform a search on sale.order in order to comply with access rights as tx do not have any
                ('sale_order_ids', 'in', request.env['sale.order'].search(sale_order_domain + [('state', '!=', 'cancel')]).ids),
            ]),
            total_sold=price_subtotal,
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

        sales_values['graph'] += [{
            'values': self._compute_sale_graph(date_date_from, date_date_to, sale_report_domain),
            'key': 'Untaxed Total',
        }, {
            'values': self._compute_sale_graph(date_date_from - timedelta(days=date_diff_days), date_date_from, sale_report_domain, previous=True),
            'key': previous_sale_label,
        }]

        return results

    def fetch_utm_data(self, date_from, date_to):
        sale_utm_domain = [
            ('website_id', '!=', False),
            ('state', '=', 'sale'),
            ('date_order', '>=', date_from),
            ('date_order', '<=', date_to)
        ]

        orders_data_groupby_campaign_id = request.env['sale.order']._read_group(
            domain=sale_utm_domain + [('campaign_id', '!=', False)],
            groupby=['campaign_id'],
            aggregates=['amount_total:sum'])

        orders_data_groupby_medium_id = request.env['sale.order']._read_group(
            domain=sale_utm_domain + [('medium_id', '!=', False)],
            groupby=['medium_id'],
            aggregates=['amount_total:sum'])

        orders_data_groupby_source_id = request.env['sale.order']._read_group(
            domain=sale_utm_domain + [('source_id', '!=', False)],
            groupby=['source_id'],
            aggregates=['amount_total:sum'])

        return {
            'campaign_id': self.compute_utm_graph_data(orders_data_groupby_campaign_id),
            'medium_id': self.compute_utm_graph_data(orders_data_groupby_medium_id),
            'source_id': self.compute_utm_graph_data(orders_data_groupby_source_id),
        }

    def compute_utm_graph_data(self, utm_graph_data):
        return [{
            'utm_type': utm_type.display_name,
            'amount_total': amount_total,
        } for utm_type, amount_total in utm_graph_data]

    def _compute_sale_graph(self, date_from, date_to, sales_domain, previous=False):
        days_between = (date_to - date_from).days
        date_list = [(date_from + timedelta(days=x)) for x in range(0, days_between + 1)]

        daily_sales = request.env['sale.report']._read_group(
            domain=sales_domain,
            groupby=['date:day'],
            aggregates=['price_subtotal:sum'])

        daily_sales_dict = {date_day: price_subtotal_sum for date_day, price_subtotal_sum in daily_sales}

        sales_graph = [{
            '0': fields.Date.to_string(d) if not previous else fields.Date.to_string(d + timedelta(days=days_between)),
            # Respect read_group format in models.py
            '1': daily_sales_dict.get(d, 0),
        } for d in date_list]

        return sales_graph
