# -*- coding: utf-8 -*-

from openerp import http
from openerp.http import request


class WebDashboard(http.Controller):

    @http.route('/web_settings_dashboard/data', type='json', auth='user')
    def web_settings_dashboard_data(self, **kw):

        installed_apps = request.env['ir.module.module'].search_count([
            ('application', '=',  True),
            ('state', 'in', ['installed', 'to upgrade', 'to remove'])
        ])
        active_users = request.env['res.users'].search_count([('active', '=', True), ('login_date', '!=', False)])
        inactive_users = request.env['res.users'].search([('login_date', '=', False)], order="create_date desc")
        pending_users = inactive_users.filtered(lambda u: u.signup_valid)
        expired_users = inactive_users - pending_users
        users_by_state = {
            'expired': zip(expired_users.mapped('id'), expired_users.mapped('login')),
            'pending': zip(pending_users.mapped('id'), pending_users.mapped('login')),
        }

        return {
            'apps': {
                'installed_apps': installed_apps
            },
            'users_info': {
                'active_users': active_users,
                'users': users_by_state,
                'template_user_id': request.env['ir.config_parameter'].get_param('auth_signup.template_user_id'),
                'user_form_id': request.env['ir.model.data'].xmlid_to_res_id("base.view_users_form")
            },
            'gift': {
                'user_email': request.env.user.email
            }
        }
