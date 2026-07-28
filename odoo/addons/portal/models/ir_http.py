# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        mods = super(IrHttp, cls)._get_translation_frontend_modules_name()
        return mods + ['portal']

    @classmethod
    def _get_frontend_langs(cls):
        # _get_frontend_langs() is used by @http_routing:IrHttp._match
        # where is_frontend is not yet set and when no backend endpoint
        # matched. We have to assume we are going to match a frontend
        # route, hence the default True. Elsewhere, request.is_frontend
        # is set.
        if request and getattr(request, 'is_frontend', True):
            return [lang[0] for lang in filter(lambda l: l[3], request.env['res.lang'].get_available())]
        return super()._get_frontend_langs()
