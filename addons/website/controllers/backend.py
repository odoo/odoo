# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import http, _
from odoo.http import request


class WebsiteBackend(http.Controller):

    @http.route('/website/fetch_dashboard_data', type="json", auth='user')
    def fetch_dashboard_data(self, date_from, date_to):

        params = request.env['ir.config_parameter']
        ga_client_id = params.sudo().get_param('google_management_client_id', default='')
        system = request.env['res.users'].has_group('website.group_website_designer')
        is_admin = request.env['res.users'].has_group('base.group_system')
        APPS_ICON = {}
        apps = []
        if is_admin:
            APPS_ICON = {
                'website_crm': {'icon': 'fa-file-text-o', 'help': _('Add a contact form to your Contact Us page.')},
                'website_sale': {'icon': 'fa-shopping-cart', 'help': _('Sell online to reach new customers.')},
                'website_blog': {'icon': 'fa-rss-square', 'help': _('Build up a community with an efficient content strategy.')},
                'website_hr_recruitment': {'icon': 'fa-suitcase', 'help': _('Promote your job announces to attract new talents.')},
                'website_event': {'icon': 'fa-ticket', 'help': _('Promote your events, manage attendance and sell tickets.')},
                'im_livechat': {'icon': 'fa-comments-o', 'help': _('Chat with your visitors in real time.')}
            }
            cookie_content = request.httprequest.cookies.get('o_dashboard_hide_panel')
            ignore_ids = cookie_content and json.loads(cookie_content) or []
            apps = request.env['ir.module.module'].search_read([
                ('id', 'not in', ignore_ids),
                ('name', 'in', ['website_crm', 'website_sale', 'website_blog', 'website_hr_recruitment', 'website_event', 'im_livechat']),
                ('state', 'not in', ['installed', 'to upgrade'])], ['id', 'sequence', 'name', 'shortdesc'], order='sequence ASC')
        if system:
            return {
                'groups': {'system': system, 'is_admin': is_admin},
                'dashboards': {
                    'visits': {
                        'ga_client_id': ga_client_id,
                    },
                    'apps': apps,
                    'apps_icon': APPS_ICON,
                },
            }
        return {}
