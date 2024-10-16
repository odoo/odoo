# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import utm, mail, web_tour, web_editor


class IrHttp(mail.IrHttp, utm.IrHttp, web_editor.IrHttp, web_tour.IrHttp):

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        mods = super()._get_translation_frontend_modules_name()
        return mods + ["mass_mailing"]
