# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import warnings

import werkzeug
import werkzeug.exceptions
import werkzeug.utils
import werkzeug.wrappers
import werkzeug.wsgi

import odoo
import odoo.modules.registry
from odoo import http
from odoo.modules import get_manifest, get_resource_path
from odoo.http import request
from odoo.tools import lazy
from odoo.tools.misc import file_open
from .utils import _local_web_translations


_logger = logging.getLogger(__name__)


@lazy
def CONTENT_MAXAGE():
    warnings.warn("CONTENT_MAXAGE is a deprecated alias to odoo.http.STATIC_CACHE_LONG", DeprecationWarning)
    return http.STATIC_CACHE_LONG


class WebClient(http.Controller):

    @http.route('/web/webclient/locale/<string:lang>', type='http', auth="none")
    def load_locale(self, lang):
        magic_file_finding = [lang.replace("_", '-').lower(), lang.split('_')[0]]
        for code in magic_file_finding:
            try:
                return http.Response(
                    werkzeug.wsgi.wrap_file(
                        request.httprequest.environ,
                        file_open(f'web/static/lib/moment/locale/{code}.js', 'rb')
                    ),
                    content_type='application/javascript; charset=utf-8',
                    headers=[('Cache-Control', f'max-age={http.STATIC_CACHE}')],
                    direct_passthrough=True,
                )
            except IOError:
                _logger.debug("No moment locale for code %s", code)

        return request.make_response("", headers=[
            ('Content-Type', 'application/javascript'),
            ('Cache-Control', f'max-age={http.STATIC_CACHE}'),
        ])

    @http.route('/web/webclient/bootstrap_translations', type='json', auth="none")
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
            mods = odoo.conf.server_wide_modules or []
            if request.db:
                mods = request.env.registry._init_modules.union(mods)

        translations_per_module = {}
        for addon_name in mods:
            manifest = get_manifest(addon_name)
            if manifest and manifest['bootstrap']:
                f_name = get_resource_path(addon_name, 'i18n', f'{lang}.po')
                if not f_name:
                    continue
                translations_per_module[addon_name] = {'messages': _local_web_translations(f_name)}

        return {"modules": translations_per_module,
                "lang_parameters": None}

    @http.route('/web/webclient/translations/<string:unique>', type='http', auth="public", cors="*")
    def translations(self, unique, mods=None, lang=None):
        """
        Load the translations for the specified language and modules

        :param unique: this parameters is not used, but mandatory: it is used by the HTTP stack to make a unique request
        :param mods: the modules, a comma separated list
        :param lang: the language of the user
        :return:
        """
        if mods:
            mods = mods.split(',')
        elif mods is None:
            mods = list(request.env.registry._init_modules) + (odoo.conf.server_wide_modules or [])

        translations_per_module, lang_params = request.env["ir.translation"].get_translations_for_webclient(mods, lang)

        body = json.dumps({
            'lang': lang,
            'lang_parameters': lang_params,
            'modules': translations_per_module,
            'multi_lang': len(request.env['res.lang'].sudo().get_installed()) > 1,
        })
        response = request.make_response(body, [
            # this method must specify a content-type application/json instead of using the default text/html set because
            # the type of the route is set to HTTP, but the rpc is made with a get and expects JSON
            ('Content-Type', 'application/json'),
            ('Cache-Control', f'public, max-age={http.STATIC_CACHE_LONG}'),
        ])
        return response

    @http.route('/web/webclient/version_info', type='json', auth="none")
    def version_info(self):
        return odoo.service.common.exp_version()

    @http.route('/web/tests', type='http', auth="user")
    def test_suite(self, mod=None, **kwargs):
        return request.render('web.qunit_suite')

    @http.route('/web/tests/mobile', type='http', auth="none")
    def test_mobile_suite(self, mod=None, **kwargs):
        return request.render('web.qunit_mobile_suite')

    @http.route('/web/benchmarks', type='http', auth="none")
    def benchmarks(self, mod=None, **kwargs):
        return request.render('web.benchmark_suite')

    @http.route('/web/bundle/<string:bundle_name>', auth="public", methods=["GET"])
    def bundle(self, bundle_name, **bundle_params):
        """
        Request the definition of a bundle, including its javascript and css bundled assets
        """
        if 'lang' in bundle_params:
            request.update_context(lang=bundle_params['lang'])

        debug = bundle_params.get('debug', request.session.debug)
        files = request.env["ir.qweb"]._get_asset_nodes(bundle_name, debug=debug, js=True, css=True)
        data = [{
            "type": tag,
            "src": attrs.get("src") or attrs.get("data-src") or attrs.get('href'),
            "content": content,
        } for tag, attrs, content in files]

        return request.make_json_response(data)
