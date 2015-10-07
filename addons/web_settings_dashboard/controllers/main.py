# -*- coding: utf-8 -*-

from openerp import http
from openerp.http import request


class WebSettingsDashboard(http.Controller):

    @http.route('/web_settings_dashboard/data', type='json', auth='user')
    def web_settings_dashboard_data(self, **kw):

        installed_apps = request.env['ir.module.module'].search_count([
            ('application', '=',  True),
            ('state', 'in', ['installed', 'to upgrade', 'to remove'])
        ])
        active_users = request.env['res.users'].search_count([('active', '=', True), ('log_ids', '!=', False)])
        pending_users = request.env['res.users'].search([('log_ids', '=', False)], order="create_date desc")

        return {
            'apps': {
                'installed_apps': installed_apps
            },
            'users_info': {
                'active_users': active_users,
                'pending_users': zip(pending_users.mapped('id'), pending_users.mapped('login')),
                'user_form_view_id': request.env['ir.model.data'].xmlid_to_res_id("base.view_users_form"),
            },
        }
