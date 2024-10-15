# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons import portal


class IrHttp(portal.IrHttp):

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        mods = super()._get_translation_frontend_modules_name()
        return mods + ['auth_password_policy']
