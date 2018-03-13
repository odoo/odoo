# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo import http
from odoo.http import request
from odoo.osv import expression
from odoo.addons.web.controllers.main import WebClient, Home

class Routing(Home):

    @http.route('/website/translations', type='json', auth="public", website=True)
    def get_website_translations(self, lang, mods=None):
        Modules = request.env['ir.module.module'].sudo()
        IrHttp = request.env['ir.http'].sudo()
        domain = IrHttp._get_translation_frontend_modules_domain()
        modules = Modules.search(
            expression.AND([domain, [('state', '=', 'installed')]])
        ).mapped('name')
        if mods:
            modules += mods
        return WebClient().translations(mods=modules, lang=lang)
