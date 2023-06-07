# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import suppress

from odoo import models, api
from odoo.exceptions import MissingError
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        mods = super()._get_translation_frontend_modules_name()
        return mods + ['portal']

    @api.model
    def get_frontend_session_info(self):
        result = super().get_frontend_session_info()
        if request.session.uid:
            result["tour_enabled"] = self.env.user.tour_enabled
            if self.env.user.tour_enabled:
                result["current_tour"] = self.env["web_tour.tour"].get_current_tour()
        return result

    @classmethod
    def _portal_localize_url(cls, url, lang):
        """Localize the URL with the language (or nearest) if it is available in the frontend languages.

        :param str url: URL to localize
        :param str lang: lang code (ex.: fr_BE)
        :return: localized URL
        :rtype: str

        See url_for documentation for more information as it relies on it. """
        lang_code = request.env['ir.http'].get_nearest_lang(lang)
        return cls._url_for(url, lang_code=lang_code) if lang_code else url

    @classmethod
    def _portal_localize_url_for_partner(cls, url, pid):
        """ Localize the URL for the partner (pid: int), see _portal_localize_url for more details."""
        with suppress(MissingError):
            return cls._portal_localize_url(url, request.env['res.partner'].sudo().browse([int(pid)]).lang)
        return url
