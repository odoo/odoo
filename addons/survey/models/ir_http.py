# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import api, models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @api.model
    def get_nearest_lang(self, lang_code):
        if request and self._is_survey_frontend(request.httprequest.path):
            return super(IrHttp, self.with_context(web_force_installed_langs=True)).get_nearest_lang(lang_code)
        return super().get_nearest_lang(lang_code)

    @api.model
    def _is_survey_frontend(self, path):
        return bool(re.match('/survey/|/[a-z]{2}/survey/|/[a-z]{2}_[A-Z]{2}/survey/', path))
