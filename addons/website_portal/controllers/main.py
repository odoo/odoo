# -*- coding: utf-8 -*-
import openerp
from openerp import http
from openerp.addons.web.http import request
from openerp.addons.web.controllers.main import ensure_db, login_redirect
import werkzeug.utils


class Portal(openerp.addons.website.controllers.main.Website):
    
    @http.route('/web', type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        if request.session.uid:
            cr, uid = request.cr, request.session.uid
            portal_user = request.registry['res.users'].has_group(cr, uid, 'base.group_portal')
            normal_user = request.registry['res.users'].has_group(cr, uid, 'base.group_user')
            if portal_user and not normal_user:
                return werkzeug.utils.redirect('/portal')
            else:
                return super(Portal,self).web_client(s_action)
        else:
            return login_redirect()

    @http.route('/portal', auth='public', website=True)
    def portal(self, **kw):
        if request.session.uid:
            cr, uid = request.cr, request.session.uid
            portal_user = request.registry['res.users'].has_group(cr, uid, 'base.group_portal')
            if not portal_user:
                return request.render("website.403")

            # for a normal user with portal access, redirect to backend
            normal_user = request.registry['res.users'].has_group(cr, uid, 'base.group_user')
            if normal_user:
                return werkzeug.utils.redirect('/web')

            portal_menu = request.env['ir.ui.menu'].load_menus()
            return request.render("website.portal", qcontext={'portal_menu_data': portal_menu})
        else:
            return login_redirect()
