# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _dispatch(cls):
        context = dict(request.context)
        if 'editable' in request.httprequest.args and 'editable' not in context:
            context['editable'] = True
        if 'edit_translations' in request.httprequest.args and 'edit_translations' not in context:
            context['edit_translations'] = True
        if context.get('lang') != "en_US" and 'translatable' not in context:
            context['translatable'] = True
        request.context = context
        return super(IrHttp, cls)._dispatch()
