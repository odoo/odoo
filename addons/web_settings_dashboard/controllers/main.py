# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from openerp import http
from openerp.exceptions import AccessError
from openerp.http import request
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT


class WebSettingsDashboard(http.Controller):

    @http.route('/web_settings_dashboard/data', type='json', auth='user')
    def web_settings_dashboard_data(self, **kw):
        if not request.env.user.has_group('base.group_erp_manager'):
            raise AccessError("Access Denied")

        installed_apps = request.env['ir.module.module'].search_count([
            ('application', '=', True),
            ('state', 'in', ['installed', 'to upgrade', 'to remove'])
        ])
        cr = request.cr
        cr.execute("""
            SELECT exists(SELECT 1 FROM res_users_log WHERE create_uid=u.id), count(1)
              FROM res_users u
             WHERE active=true
          GROUP BY 1
        """)
        counts = dict(cr.fetchall())

        cr.execute("""
           SELECT id, login
             FROM res_users u
            WHERE active=true
              AND NOT exists(SELECT 1 FROM res_users_log WHERE create_uid=u.id)
         ORDER BY id desc
            LIMIT 10
        """)
        pending_users = cr.fetchall()

        # See update.py for this computation
        limit_date = datetime.now() - timedelta(15)
        enterprise_users = request.env['res.users'].search_count([("login_date", ">=", limit_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)), ('share', '=', False)])

        return {
            'apps': {
                'installed_apps': installed_apps
            },
            'users_info': {
                'active_users': counts.get(True, 0),
                'pending_count': counts.get(False, 0),
                'pending_users': pending_users,
                'user_form_view_id': request.env['ir.model.data'].xmlid_to_res_id("base.view_users_form"),
            },
            'enterprise': {
                'enterprise_users': enterprise_users,
            }
        }
