# -*- coding: utf-8 -*-

from openerp import http
from openerp.http import request


class Dashboard(http.Controller):

    @http.route('/dashboard/info', type='json', auth='user')
    def get_info(self, **kw):
        installed_apps = request.env['ir.module.module'].search_count([('application', '=',  True), ('state', 'in', ['installed', 'to upgrade', 'to remove'])])
        active_users = request.env['res.users'].search_count([('active', '=', True), ('login_date', '!=', False)])
        return {
            'apps': {
                'installed_apps': installed_apps
            },
            'users_info': {
                'active_users': active_users,
                'users': request.env['res.users'].web_dashboard_get_users_by_state(),
                'template_user_id': request.env['ir.config_parameter'].get_param('auth_signup.template_user_id'),
                'user_form_id': request.env['ir.model.data'].xmlid_to_res_id("base.view_users_form")
            },
            'gift': {
                'user_email': request.env.user.email
            }
        }
