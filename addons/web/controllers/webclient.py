# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from hashlib import sha256

import odoo.tools
from odoo import http, release
from odoo.http import request
from odoo.http.stream import STATIC_CACHE_LONG
from odoo.modules import Manifest
from odoo.tools.misc import file_path


from .utils import _local_web_translations

_logger = logging.getLogger(__name__)


class WebClient(http.Controller):

    @http.route('/web/webclient/bootstrap_translations', type='jsonrpc', auth="none")
    def bootstrap_translations(self, mods=None):
        """ Load local translations from *.po files, as a temporary solution
            until we have established a valid session. This is meant only
            for translating the login page and db management chrome, using
            the browser's language. """
        # For performance reasons we only load a single translation, so for
        # sub-languages (that should only be partially translated) we load the
        # main language PO instead - that should be enough for the login screen.
        lang = request.env.context['lang'].partition('_')[0]

        if mods is None:
            mods = odoo.tools.config['server_wide_modules']
            if request.db:
                mods = request.env.registry._init_modules.union(mods)

        translations_per_module = {}
        for addon_name in mods:
            manifest = Manifest.for_addon(addon_name)
            if manifest and manifest['bootstrap']:
                f_name = file_path(f'{addon_name}/i18n/{lang}.po')
                if not f_name:
                    continue
                translations_per_module[addon_name] = {'messages': _local_web_translations(f_name)}

        return {"modules": translations_per_module,
                "lang_parameters": None}

    @http.route('/web/webclient/translations', type='http', auth='public', cors='*', readonly=True)
    def translations(self, hash=None, mods=None, lang=None):
        """
        Load the translations for the specified language and modules

        :param hash: translations hash, which identifies a version of translations. This method only returns translations if their hash differs from the received one
        :param mods: the modules, a comma separated list
        :param lang: the language of the user
        :return:
        """
        if mods:
            mods = mods.split(',')
        else:
            mods = request.env.registry._init_modules.union(odoo.tools.config['server_wide_modules'])

        if lang and lang not in {code for code, _ in request.env['res.lang'].sudo().get_installed()}:
            lang = None

        current_hash = request.env["ir.http"].with_context(cache_translation_data=True)._get_web_translations_hash(mods, lang)

        body = {
            'lang': lang,
            'hash': current_hash,
        }
        if current_hash != hash:
            if 'translation_data' in request.env.cr.cache:
                # ormcache of _get_web_translations_hash was cold and fill the translation_data cache
                body.update(request.env.cr.cache.pop('translation_data'))
            else:
                # ormcache of _get_web_translations_hash was hot
                translations_per_module, lang_params = request.env["ir.http"]._get_translations_for_webclient(mods, lang)
                body.update({
                    'lang_parameters': lang_params,
                    'modules': translations_per_module,
                    'multi_lang': len(request.env['res.lang'].sudo().get_installed()) > 1,
                })

        # The type of the route is set to HTTP, but the rpc is made with a get and expects JSON
        return request.make_json_response(body, [
            ('Cache-Control', f'public, max-age={STATIC_CACHE_LONG}'),
        ])

    @http.route('/web/webclient/version_info', type='jsonrpc', auth="none")
    def version_info(self):
        return {
            'server_version': release.version,
            'server_version_info': release.version_info,
            'server_serie': release.serie,
        }

    @http.route('/web/tests', type='http', auth='user', readonly=True)
    def unit_tests_suite(self, mod=None, **kwargs):
        return request.render('web.unit_tests_suite', {
            'session_info': {
                "server_version": release.version,
                "server_version_info": release.version_info,
                'view_info': request.env['ir.ui.view'].get_view_info()
            },
        })

    @http.route('/web/bundle/<string:bundle_name>', auth='public', methods=['GET'], readonly=True)
    def bundle(self, bundle_name, **bundle_params):
        """
        Request the definition of a bundle, including its javascript and css bundled assets
        """
        if 'lang' in bundle_params:
            request.update_context(lang=request.env['res.lang']._get_code(bundle_params['lang']))

        debug = bundle_params.get('debug', request.session.debug)
        files = request.env["ir.qweb"]._get_asset_nodes(bundle_name, debug=debug, js=True, css=True)
        data = [{
            "type": tag,
            "src": attrs.get("src") or attrs.get("data-src") or attrs.get('href'),
        } for tag, attrs in files]

        return request.make_json_response(data)


def digest_term(term):
    return sha256(term.encode()).hexdigest()


class Translations(http.Controller):

    def _get_translation_mode(self, res_model, field_name):
        field = self.env[res_model]._fields[field_name]
        match (field.type, callable(field.translate)):
            case ("html", True):
                return "structured_html"
            case ("html", _):
                return "html"
            case (_, True):
                return "xml"
            case _:
                return "text"

    @http.route("/web/translations/get_translation_for_field", type="jsonrpc", methods=["POST"], auth="user", readonly=True)
    def _get_translation_for_field(self, res_model, field_name, res_id, target_lang=None, context=None):
        if context:
            request.update_context(**context)
        translation_mode = self._get_translation_mode(res_model, field_name)

        record_base_lang = self.env[res_model].browse(res_id)._get_base_lang()
        langs = self.env["res.lang"].sudo()._get_active_langs().sorted('name')
        lang_codes = langs.mapped("code")

        if target_lang is None or target_lang not in lang_codes:
            target_lang = next(iter(code for code in lang_codes if code != record_base_lang), None)

        result = {
            "target_lang": target_lang,
            "translation_mode": translation_mode,
            "languages": {l.code: {"name": l.name, "direction": l.direction, "code": l.code, "is_base": record_base_lang == l.code} for l in langs}
        }

        record = self.env[res_model].browse(res_id)
        match translation_mode:
            case "xml" | "structured_html":
                rec_context = record.with_context(lang=target_lang, edit_translations=True)
                rec_context.fetch([field_name])
                result["xml_values"] = {
                    target_lang: rec_context[field_name]
                }
                field_translations, _ = record.get_field_translations(field_name, [target_lang])
                for tr in field_translations:
                    tr["source_sha"] = digest_term(tr["source"])
                result["terms"] = field_translations
            case "html" | "text":
                result["terms"] = record.get_field_translations(field_name, (lang.code for lang in langs))[0]
        return result

    @http.route("/web/translations/save_translation_for_field", type="jsonrpc", methods=["POST"], auth="user")
    def _save_translation_for_field(self, res_model, field_name, res_id, target_lang=None, changes=None, context=None):
        if context:
            request.update_context(**context)
        translation_mode = self._get_translation_mode(res_model, field_name)
        record = self.env[res_model].browse(res_id)
        langs = self.env["res.lang"].sudo()._get_active_langs().mapped('code')
        match translation_mode:
            case "xml" | "structured_html":
                record._update_field_translations(field_name, changes, digest=digest_term)
            case "text" | "html":
                if ("en_US" in changes and changes["en_US"] is None) or "en_US" not in langs:
                    changes["en_US"] = next(v for v in changes.values() if v is not None)
                record._update_field_translations(field_name, changes)
