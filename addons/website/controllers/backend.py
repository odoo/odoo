# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class WebsiteBackend(http.Controller):

    @http.route('/website/fetch_dashboard_data', type="json", auth='user')
    def fetch_dashboard_data(self, date_from, date_to):
        has_group_system = request.env.user.has_group('base.group_system')
        has_group_designer = request.env.user.has_group('website.group_website_designer')
        dashboard_data = {
            'groups': {
                'system': has_group_system,
                'website_designer': has_group_designer
            },
            'currency': request.env.user.company_id.currency_id.id,
            'dashboards': {
                'visits': {},
            }
        }
        if has_group_designer:
            config = request.env['res.config.settings'].sudo().create({})
            if config.has_google_analytics_dashboard:
                dashboard_data['dashboards']['visits'] = dict(
                    ga_client_id=config.google_management_client_id or '',  # void string instead of stringified False
                    ga_analytics_key=config.google_analytics_key or '',  # void string instead of stringified False
                )
        return dashboard_data

    @http.route('/website/dashboard/set_ga_data', type='json', auth='user')
    def website_set_ga_data(self, ga_client_id, ga_analytics_key):
        if not request.env.user.has_group('base.group_system'):
            return {
                'error': {
                    'title': 'Access Error',
                    'message': 'You do not have sufficient rights to perform that action.',
                }
            }
        if not ga_analytics_key or not ga_client_id.endswith('.apps.googleusercontent.com'):
            return {
                'error': {
                    'title': 'Incorrect Client ID / Key',
                    'message': 'The Google Analytics Client ID or Key you entered seems incorrect.',
                }
            }
        request.env['res.config.settings'].create({
            'has_google_analytics': True,
            'has_google_analytics_dashboard': True,
            'google_management_client_id': ga_client_id,
            'google_analytics_key': ga_analytics_key,
        }).execute()
        return True
