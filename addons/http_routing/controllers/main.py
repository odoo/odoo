# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home
from odoo.addons.web.controllers.session import Session
from odoo.addons.web.controllers.webclient import WebClient
from odoo.addons.web.controllers.webmanifest import WebManifest


class Routing(Home):

    @http.route('/website/translations', type='http', auth="public", readonly=True, sitemap=False)
    def get_website_translations(self, hash=None, lang=None, mods=None):
        IrHttp = request.env['ir.http'].sudo()
        modules = IrHttp.get_translation_frontend_modules()
        if mods:
            modules += mods.split(',')
        return WebClient().translations(hash, mods=','.join(modules), lang=lang)


class SessionWebsite(Session):

    @http.route('/web/session/logout', website=True, multilang=False, sitemap=False)
    def logout(self, redirect='/odoo'):
        return super().logout(redirect=redirect)


class WebManifestWebsite(WebManifest):

    @http.route('/scoped_app', website=True, multilang=False, sitemap=False)
    def scoped_app(self, app_id, path='', app_name=''):
        return super().scoped_app(app_id=app_id, path=path, app_name=app_name)
