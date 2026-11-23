# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request


CONTEXT_KEYS = ['editable', 'edit_translations', 'translatable']


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_web_editor_context(cls):
        """ Check for ?editable and stuff in the query-string """
        return {
            key: True
            for key in CONTEXT_KEYS
            if key in request.httprequest.args and key not in request.env.context
        }

    @classmethod
    def _pre_dispatch(cls, rule, args):
        super()._pre_dispatch(rule, args)
        ctx = cls._get_web_editor_context()
        request.update_context(**ctx)

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        mods = super(IrHttp, cls)._get_translation_frontend_modules_name()
        return mods + ['web_editor']
