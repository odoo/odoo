# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request


class BaseSetup(http.Controller):
    @http.route('/base_setup/data', type='json', auth='user')
    def base_setup_data(self, **kw):
        if not request.env.user.has_group('base.group_erp_manager'):
            raise AccessError(_("Access Denied"))

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

        return {
            'active_users': active_count,
            'pending_count': pending_count,
            'pending_users': pending_users,
        }

    @http.route('/base_setup/demo_active', type='json', auth='user')
    def base_setup_is_demo(self, **kwargs):
        # We assume that if there's at least one module with demo data active, then the db was
        # initialized with demo=True or it has been force-activated by the `Load demo data` button
        # in the settings dashboard.
        demo_active = bool(request.env['ir.module.module'].search_count([('demo', '=', True)]))
        return demo_active
