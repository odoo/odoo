# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request


CONTEXT_KEYS = ['editable', 'edit_translations', 'translatable']


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def _get_web_editor_context(self):
        """ Check for ?editable and stuff in the query-string """
        return {
            key: True
            for key in CONTEXT_KEYS
            if key in request.httprequest.args and key not in request.env.context
        }

    def _pre_dispatch(self, rule, args):
        super()._pre_dispatch(rule, args)
        ctx = self._get_web_editor_context()
        request.update_context(**ctx)

    def _get_translation_frontend_modules_name(self):
        mods = super()._get_translation_frontend_modules_name()
        return mods + ['web_editor']
