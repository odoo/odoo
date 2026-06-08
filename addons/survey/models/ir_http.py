# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import api, models
from odoo.http import request

SURVEY_URL_PREFIX_REGEX = re.compile(r"""
    ^
    (                            # Optional locale part of the URL
        /[a-z]{2,3}              # Language (only 2- or 3-letter ISO 639 code)
                                 #     e.g. fr, kab
        (_([A-Z]{2}|[0-9]{3}))?  # [Optional] Region (2-letter ISO 3166-1 code or 3-digit UN M.49 code)
                                 #     e.g. fr_BE, es_419
        (@[a-zA-Z]+)?            # [Optional] Script (ISO 15924 code)
                                 #     e.g. sr@Cyrl
    )?
    /survey/
""", re.VERBOSE)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @api.model
    def get_nearest_lang(self, lang_code):
        if request and self._is_survey_frontend(request.httprequest.path):
            return super(IrHttp, self.with_context(web_force_installed_langs=True)).get_nearest_lang(lang_code)
        return super().get_nearest_lang(lang_code)

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        mods = super()._get_translation_frontend_modules_name()
        return mods + ['survey']

    @api.model
    def _is_survey_frontend(self, path):
        return bool(SURVEY_URL_PREFIX_REGEX.match(path))
