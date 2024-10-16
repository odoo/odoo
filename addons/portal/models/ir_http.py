# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import web, web_editor, http_routing, auth_signup, mail


class IrHttp(web.IrHttp, web_editor.IrHttp, http_routing.IrHttp, mail.IrHttp, auth_signup.IrHttp):

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        mods = super()._get_translation_frontend_modules_name()
        return mods + ['portal']
