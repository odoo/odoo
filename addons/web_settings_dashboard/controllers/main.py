# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import _, fields, http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo import release

class WebSettingsDashboard(http.Controller):

    @http.route('/web_settings_dashboard/data', type='json', auth='user')
    def web_settings_dashboard_data(self, **kw):
        if not request.env.user.has_group('base.group_erp_manager'):
            raise AccessError(_("Access Denied"))

        installed_apps = request.env['ir.module.module'].search_count([
            ('application', '=', True),
            ('state', 'in', ['installed', 'to upgrade', 'to remove'])
        ])
        cr = request.cr
        cr.execute("""
            SELECT count(*)
              FROM res_users
             WHERE active=true AND
                   share=false
        """)
        active_count = cr.dictfetchall()[0].get('count')

        cr.execute("""
            SELECT count(u.*)
            FROM res_users u
            WHERE active=true AND
                  share=false AND
                  NOT exists(SELECT 1 FROM res_users_log WHERE create_uid=u.id)
        """)
        pending_count = cr.dictfetchall()[0].get('count')

        cr.execute("""
           SELECT id, login
             FROM res_users u
            WHERE active=true AND
                  share=false AND
                  NOT exists(SELECT 1 FROM res_users_log WHERE create_uid=u.id)
         ORDER BY id desc
            LIMIT 10
        """)
        pending_users = cr.fetchall()

        # See update.py for this computation
        limit_date = datetime.now() - timedelta(15)
        enterprise_users = request.env['res.users'].search_count([("login_date", ">=", fields.Datetime.to_string(limit_date)), ('share', '=', False)])

        expiration_date = request.env['ir.config_parameter'].sudo().get_param('database.expiration_date')

        # We assume that if there's at least one module with demo data active, then the db was
        # initialized with demo=True or it has been force-activated by the `Load demo data` button
        # in the settings dashboard.
        demo_active = bool(request.env['ir.module.module'].search_count([('demo', '=', True)]))

        return {
            'apps': {
                'installed_apps': installed_apps,
                'enterprise_users': enterprise_users,
            },
            'users_info': {
                'active_users': active_count,
                'pending_count': pending_count,
                'pending_users': pending_users,
                'user_form_view_id': request.env['ir.model.data'].xmlid_to_res_id("base.view_users_form"),
            },
            'share': {
                'server_version': release.version,
                'expiration_date': expiration_date,
                'debug': request.debug,
                'demo_active': demo_active,
            },
            'company': {
                'company_id': request.env.user.company_id.id,
                'company_name': request.env.user.company_id.name
            }
        }
