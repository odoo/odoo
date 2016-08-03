# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def _dispatch(self):
        if 'editable' in request.httprequest.args and 'editable' not in request.context:
            request.context['editable'] = True
        if 'edit_translations' in request.httprequest.args and 'edit_translations' not in request.context:
            request.context['edit_translations'] = True
        if request.context.get('lang') != "en_US" and 'translatable' not in request.context:
            request.context['translatable'] = True
        return super(IrHttp, self)._dispatch()
