# Part of Odoo. See LICENSE file for full copyright and licensing details.
<<<<<<< d87b3fb55bf4578427099731daf4438cf1b6fff1
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
||||||| b847890bf1781cac78ab5e4f9e7ae52e4599369c
=======

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        modules = super()._get_translation_frontend_modules_name()
        return modules + ["survey"]
>>>>>>> f245c8e39dbbfc50a0cb77002596b856220118e0
