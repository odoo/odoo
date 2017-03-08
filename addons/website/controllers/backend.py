# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class WebsiteBackend(http.Controller):

    @http.route('/website/fetch_dashboard_data', type="json", auth='user')
    def fetch_dashboard_data(self, date_from, date_to):
        has_group_system = request.env['res.users'].has_group('base.group_system')
        has_group_designer = request.env['res.users'].has_group('website.group_website_designer')
        website = request.env['website'].search([], limit=1)
        if has_group_system:
            apps_data = dict((app['name'], app) for app in request.env['ir.module.module'].sudo().search_read(
                ['|', ('name', 'ilike', 'website'), ('application', '=', True)],
                ['id', 'sequence', 'name', 'shortdesc', 'state'],
                order='sequence ASC'))
        else:
            apps_data = {}
        dashboard_data = {
            'groups': {
                'system': has_group_system,
                'website_designer': has_group_designer
            },
            'currency': request.env.user.company_id.currency_id.id,
            'dashboards': {
                'apps_data': apps_data,
                'visits': {},
            },
            'website_id': website.id
        }
        if has_group_designer:
            ga_dashboard = request.env['ir.values'].sudo().get_default('website.config.settings', 'has_google_analytics_dashboard')
            if ga_dashboard:
                dashboard_data['dashboards']['visits']['ga_client_id'] = website.google_management_client_id and website.google_management_client_id or ''
                dashboard_data['dashboards']['visits']['ga_analytics_key'] = website.google_analytics_key and website.google_analytics_key or ''
        return dashboard_data
