# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import url_for


class View(models.Model):
    _inherit = "ir.ui.view"

    @api.model
    def _prepare_qcontext(self):
        """ Returns the qcontext : rendering context with portal specific value (required
            to render portal layout template)
        """
        qcontext = super(View, self)._prepare_qcontext()
        if request and getattr(request, 'is_frontend', False):
            qcontext.update(dict(
                self._context.copy(),
                languages=request.env['res.lang'].get_available(),
                url_for=url_for,
            ))
        return qcontext
