# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import base

from odoo import models


class IrHttp(models.AbstractModel, base.IrHttp):

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        mods = super(IrHttp, cls)._get_translation_frontend_modules_name()
        return mods + ['portal']
