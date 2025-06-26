# Part of Odoo. See LICENSE file for full copyright and licensing details.

import mimetypes
import re

from urllib.parse import unquote
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers import webmanifest


class WebManifest(webmanifest.WebManifest):
    def _get_scoped_app_name(self, app_id):
        if app_id == "pos_self_order":
            if match := re.findall(r'pos-self/(\d+)', unquote(request.params['path'])):
                if record := request.env['pos.config'].search([('id', '=', match[0])]):
                    return record.name
        return super()._get_scoped_app_name(app_id)

    def _get_scoped_app_icons(self, app_id):
        if app_id == "pos_self_order":
            company = request.env.company
            if company.uses_default_logo:
                icon_src = '/point_of_sale/static/description/icon.svg'
            else:
                icon_src = f'/web/image?model=res.company&id={company.id}&field=logo&height=192&width=192'
            return [{
                'src': icon_src,
                'sizes': 'any',
                'type': mimetypes.guess_type(icon_src)[0] or 'image/png'
            }]
        return super()._get_scoped_app_icons(app_id)

    @http.route()
    def scoped_app_icon_png(self, app_id):
        if app_id == "pos_self_order" and request.env.company.uses_default_logo:
            return super().scoped_app_icon_png('point_of_sale')
        return super().scoped_app_icon_png(app_id)
