# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import suppress

from odoo import models
from odoo.exceptions import MissingError
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        mods = super()._get_translation_frontend_modules_name()
        return mods + ['portal']

    @classmethod
    def _frontend_localize_url(cls, url, lang):
        """ Localize the URL with the language if it is available in the frontend languages.

        :param str url: URL to localize
        :param str lang: lang code (ex.: fr_BE)
        :return: localized URL
        :rtype: str

        See url_for documentation for more information as it relies on it. """
        if not lang:
            return url
        original_is_frontend = request.is_frontend
        try:
            # Specifying "request.is_frontend = True" is necessary for the "_get_frontend" method
            # to return AVAILABLE languages otherwise it returns INSTALLED languages, which might lead
            # to a 404 if the website/portal does not support it.
            request.is_frontend = True
            if lang and lang in request.env['res.lang']._get_frontend():
                return cls._url_for(url, lang_code=lang)
            return url
        finally:
            request.is_frontend = original_is_frontend

    @classmethod
    def _frontend_localize_url_for_partner(cls, url, pid):
        """ Localize the URL for the partner (pid: int), see _frontend_localize_url for more details. """
        with suppress(MissingError):
            return cls._frontend_localize_url(url, request.env['res.partner'].sudo().browse([int(pid)]).lang)
        return url
