# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class WebsiteBackend(http.Controller):

    @http.route('/website/fetch_dashboard_data', type="json", auth='user')
    def fetch_dashboard_data(self, date_from, date_to):

        params = request.env['ir.config_parameter']
        ga_client_id = params.sudo().get_param('google_management_client_id', default='')

        return {
            'groups': {'system': request.env['res.users'].has_group('base.group_system')},
            'currency': request.env.user.company_id.currency_id.id,
            'dashboards': {
                'visits': {
                    'ga_client_id': ga_client_id,
                }
            }
        }
