# -*- coding: ascii -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import slug, unslug_url, url_for
from odoo.tools import is_html_empty


class IrUiView(models.Model):
    _inherit = ["ir.ui.view"]

    @api.model
    def _prepare_qcontext(self):
        qcontext = super(IrUiView, self)._prepare_qcontext()
        qcontext['slug'] = slug
        qcontext['unslug_url'] = unslug_url
        if request and getattr(request, 'is_frontend', False):
            Lang = request.env['res.lang']
            portal_lang_code = request.env['ir.http']._get_frontend_langs()
            qcontext.update(dict(
                self._context.copy(),
                languages=[lang for lang in Lang.get_available() if lang[0] in portal_lang_code],
                url_for=url_for,
                is_html_empty=is_html_empty,
            ))
        return qcontext
