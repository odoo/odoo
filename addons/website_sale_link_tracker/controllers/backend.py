# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.website_sale.controllers.backend import WebsiteSaleBackend
from odoo.http import request


class WebsiteSaleLinkTrackerBackend(WebsiteSaleBackend):

    @http.route()
    def fetch_dashboard_data(self, website_id, date_from, date_to):
        results = super(WebsiteSaleLinkTrackerBackend, self).fetch_dashboard_data(website_id, date_from, date_to)
        results['dashboards']['sales']['utm_graph'] = self.fetch_utm_data(date_from, date_to)
        return results

    def fetch_utm_data(self, date_from, date_to):
        sale_utm_domain = [
            ('team_id.team_type', '=', 'website'),
            ('state', 'in', ['sale', 'done']),
            ('confirmation_date', '>=', date_from),
            ('confirmation_date', '<=', date_to)
        ]

        orders_data_groupby_campaign_id = request.env['sale.order'].read_group(
            domain=sale_utm_domain + [('campaign_id', '!=', False)],
            fields=['amount_total', 'id', 'campaign_id'],
            groupby='campaign_id')

        orders_data_groupby_medium_id = request.env['sale.order'].read_group(
            domain=sale_utm_domain + [('medium_id', '!=', False)],
            fields=['amount_total', 'id', 'medium_id'],
            groupby='medium_id')

        orders_data_groupby_source_id = request.env['sale.order'].read_group(
            domain=sale_utm_domain + [('source_id', '!=', False)],
            fields=['amount_total', 'id', 'source_id'],
            groupby='source_id')

        return {
            'campaign_id': self.compute_utm_graph_data('campaign_id', orders_data_groupby_campaign_id),
            'medium_id': self.compute_utm_graph_data('medium_id', orders_data_groupby_medium_id),
            'source_id': self.compute_utm_graph_data('source_id', orders_data_groupby_source_id),
        }

    def compute_utm_graph_data(self, utm_type, utm_graph_data):
        return [{
            'utm_type': data[utm_type][1],
            'amount_total': data['amount_total']
        } for data in utm_graph_data]
