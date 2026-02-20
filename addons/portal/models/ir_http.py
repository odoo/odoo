# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        mods = super(IrHttp, cls)._get_translation_frontend_modules_name()
        return mods + ['portal']

    @api.model
    def get_frontend_session_info(self):
        result = super().get_frontend_session_info()
        if request.session.uid:
            result["tour_enabled"] = self.env.user.tour_enabled
            if self.env.user.tour_enabled:
                result["current_tour"] = self.env["web_tour.tour"].get_current_tour()
        return result
