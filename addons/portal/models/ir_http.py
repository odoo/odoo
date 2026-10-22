# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
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

    def _portal_localize_url(self, url, lang):
        """Localize the URL with the language (or nearest) if it is available in the frontend languages.

        :param str url: URL to localize
        :param str lang: lang code (ex.: fr_BE)
        :return: localized URL
        :rtype: str

        See url_for documentation for more information as it relies on it."""
        lang_code = self.get_nearest_lang(lang)
        if lang_code == self._get_default_lang().code:
            return url  # Don't localize the URL to avoid a redirection
        return self._url_for(url, lang_code=lang_code) if lang_code else url

    def _portal_localize_url_for_partner(self, url, pid):
        """Localize the URL for the partner (pid: int), see _portal_localize_url for more details.

        The caller must have validated the pid (ex.: with its hash) as it reveals the partner language."""
        if lang := self.env["res.partner"].sudo().browse([int(pid)]).exists().lang:
            return self._portal_localize_url(url, lang)
        return url
