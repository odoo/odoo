# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home
from odoo.addons.web.controllers.session import Session
from odoo.addons.web.controllers.webclient import WebClient


class Routing(Home):

    @http.route('/website/translations/<string:unique>', type='http', auth="public", website=True)
    def get_website_translations(self, unique, lang=None, mods=None):
        IrHttp = request.env['ir.http'].sudo()
        modules = IrHttp.get_translation_frontend_modules()
        if mods:
            modules += mods.split(',')
        return WebClient().translations(unique, mods=','.join(modules), lang=lang)


class SessionWebsite(Session):

    @http.route('/web/session/logout', website=True, multilang=False, sitemap=False)
    def logout(self, redirect='/web'):
        return super().logout(redirect=redirect)
