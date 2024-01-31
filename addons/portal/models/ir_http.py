# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import suppress

from odoo import models
from odoo.addons.http_routing.models.ir_http import url_for
from odoo.exceptions import MissingError
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        mods = super(IrHttp, cls)._get_translation_frontend_modules_name()
        return mods + ['portal']

    @classmethod
    def _get_frontend_langs(cls):
        # _get_frontend_langs() is used by @http_routing:IrHttp._match
        # where is_frontend is not yet set and when no backend endpoint
        # matched. We have to assume we are going to match a frontend
        # route, hence the default True. Elsewhere, request.is_frontend
        # is set.
        if request and getattr(request, 'is_frontend', True):
            return [lang[0] for lang in filter(lambda l: l[3], request.env['res.lang'].get_available())]
        return super()._get_frontend_langs()

    @classmethod
    def _localize_url(cls, url, lang):
        """ Localize the URL with the language if it is available in the frontend languages.

        :param str url: URL to localize
        :param str lang: lang code (ex.: fr_BE)
        :return str: localized URL

        See url_for documentation for more information as it relies on it. """
        if not lang:
            return url
        original_is_frontend = request.is_frontend
        try:
            # Specifying "request.is_frontend = True" is necessary for the "_get_frontend_langs" method
            # to return AVAILABLE languages otherwise it returns INSTALLED languages, which might lead
            # to a 404 if the website/portal does not support it.
            request.is_frontend = True
            if lang and lang in request.env['ir.http']._get_frontend_langs():
                return url_for(url, lang_code=lang)
            return url
        finally:
            request.is_frontend = original_is_frontend

    @classmethod
    def _localize_url_for_partner(cls, url, pid):
        """ Localize the URL for the partner (pid: int), see _localize_url for more details. """
        with suppress(MissingError):
            return cls._localize_url(url, request.env['res.partner'].sudo().browse([int(pid)]).lang)
        return url
