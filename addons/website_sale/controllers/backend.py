# -*- coding: utf-8 -*-
from odoo import fields, http
from odoo.http import request
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta
from math import floor
import time
import operator
import babel

from odoo.addons.website.controllers.backend import WebsiteBackend
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT


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
        date_from = datetime.strptime(date_from, DEFAULT_SERVER_DATE_FORMAT)
        date_to = datetime.strptime(date_to, DEFAULT_SERVER_DATE_FORMAT)

        # Best seller products
        product_lines = request.env['sale.order.line'].read_group(
            domain=[
                ('product_id.website_published', '=', True),
                ('order_id.state', 'in', ['sent', 'sale', 'done']),
                ('order_id.team_id', 'in', website_teams.ids),
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
            })

        # Graphes computation
        sales_domain = [
            ('team_id', 'in', website_teams.ids),
            ('state', 'in', ['sent', 'sale', 'done']),
        ]
        sales_graph = self._compute_sale_graph(date_from, date_to, sales_domain)
        previous_sales_graph = self._compute_sale_graph(date_from - timedelta(days=(date_to - date_from).days), date_from, sales_domain, previous=True)

        # calculate the sale dashboard
        values = {
            'awaiting_payments': 0,
            'order_to_invoice': 0,
            'payment_to_capture': 0,
            'abandoned_carts': 0,
            'active_carts': 0,
        }
        summary = {
            'sold': 0,
            'orders': 0,
            'carts': 0,
            'net_profit': 0,
        }

        time_constraint = fields.Datetime.to_string(fields.datetime.now() - timedelta(hours=1))
        carts_domain = [('team_id', 'in', website_teams.ids), ('state', '=', 'draft')]
        values['abandoned_carts'] = request.env['sale.order'].search_count(carts_domain + [('order_line', '!=', False), ('partner_id', '!=', request.env.ref('base.public_partner').id), ('date_order', '<', time_constraint)])
        values['active_carts'] = request.env['sale.order'].search_count(carts_domain + [('date_order', '>=', time_constraint)])

        sale_order_line_group = request.env['sale.order.line'].read_group(
            domain=[
                ('order_id.team_id', 'in', website_teams.ids),
                ('order_id.state', 'in', ['sale', 'done']),
                ('order_id.date_order', '>=', date_from.strftime(DEFAULT_SERVER_DATE_FORMAT)),
                ('order_id.date_order', '<=', date_to.strftime(DEFAULT_SERVER_DATE_FORMAT))],
            fields=['product_id', 'product_uom_qty', 'price_unit'],
            groupby='product_id')
        for sale_order_line in sale_order_line_group:
            product = request.env['product.product'].browse(sale_order_line['product_id'][0])
            summary['net_profit'] += (sale_order_line['price_unit'] - product.standard_price) * sale_order_line['product_uom_qty']

        summary['carts'] = sum(request.env['sale.order'].search([
            ('team_id', 'in', website_teams.ids),
            ('state', 'in', ['draft', 'sent', 'sale']),
            ('date_order', '>=', date_from.strftime(DEFAULT_SERVER_DATE_FORMAT)),
            ('date_order', '<=', date_to.strftime(DEFAULT_SERVER_DATE_FORMAT))]).mapped('website_order_line.product_uom_qty'))

        sale_order_group = request.env['sale.order'].read_group(
            domain=[
                ('state', 'in', ['sale', 'done']),
                ('team_id', 'in', website_teams.ids),
                ('date_order', '>=', date_from.strftime(DEFAULT_SERVER_DATE_FORMAT)),
                ('date_order', '<=', date_to.strftime(DEFAULT_SERVER_DATE_FORMAT))],
            fields=['state', 'amount_total'],
            groupby=['state'])
        for sale_order in sale_order_group:
            summary['sold'] += sale_order['amount_total']
            summary['orders'] += sale_order['state_count']

        values['order_to_invoice'] = request.env['sale.order'].search_count([
                ('state', 'in', ['sale', 'done']),
                ('team_id', 'in', website_teams.ids),
                ('invoice_status', '=', 'to invoice')])

        payment_transactions = request.env['payment.transaction'].read_group(
            domain=[('state', 'in', ['pending', 'authorized']), ('sale_order_id.state', '!=', 'cancel')],
            fields=['state'], groupby='state')
        for payment_transaction in payment_transactions:
            if payment_transaction['state'] == 'pending':
                values['awaiting_payments'] += payment_transaction['state_count']
            else:
                values['payment_to_capture'] += payment_transaction['state_count']

        results['groups']['sale_salesman'] = sale_salesman
        results['dashboards']['sales'] = {
            'graph': [
                {
                    'values': sales_graph,
                    'key': 'Sales',
                },
                {
                    'values': previous_sales_graph,
                    'key': 'Previous Sales',
                },
            ],
            'best_sellers': best_sellers,
            'values': values,
            'summary': summary,
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
