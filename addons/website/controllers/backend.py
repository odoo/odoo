# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from odoo import http
from odoo.http import request


class WebsiteBackend(http.Controller):

    @http.route('/website/fetch_dashboard_data', type="json", auth='user')
    def fetch_dashboard_data(self, website_id, date_from, date_to):
        Website = request.env['website']
        has_group_system = request.env.user.has_group('base.group_system')
        has_group_designer = request.env.user.has_group('website.group_website_designer')
        dashboard_data = {
            'groups': {
                'system': has_group_system,
                'website_designer': has_group_designer
            },
            'currency': request.env.company.currency_id.id,
            'dashboards': {}
        }

        current_website = website_id and Website.browse(website_id) or Website.get_current_website()
        multi_website = request.env.user.has_group('website.group_multi_website')
        websites = multi_website and request.env['website'].search([]) or current_website
        dashboard_data['websites'] = websites.read(['id', 'name'])
        for website in dashboard_data['websites']:
            if website['id'] == current_website.id:
                website['selected'] = True

        if has_group_designer:
            dashboard_data['dashboards']['plausible_share_url'] = current_website._get_plausible_share_url()
        return dashboard_data

    @http.route('/website/iframefallback', type="http", auth='user', website=True)
    def get_iframe_fallback(self):
        return request.render('website.iframefallback')

    @http.route('/website/check_new_content_access_rights', type="json", auth='user')
    def check_create_access_rights(self, models):
        """
        TODO: In master, remove this route and method and find a better way
        to do this. This route is only here to ensure that the "New Content"
        modal displays the correct elements for each user, and there might be
        a way to do it with the framework rather than having a dedicated
        controller route. (maybe by using a template or a JS util)
        """
        if not request.env.user.has_group('website.group_website_restricted_editor'):
            raise werkzeug.exceptions.Forbidden()

        return {
            model: request.env[model].check_access_rights('create', raise_exception=False)
            for model in models
        }
