# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging
import pprint

import werkzeug
from psycopg2.errorcodes import SERIALIZATION_FAILURE
from psycopg2.errors import SerializationFailure

from odoo import http
from odoo.exceptions import AccessError, ConcurrencyError, UserError
from odoo.http import request
from odoo.http.requestlib import fragment_to_query_string
from odoo.http.session import touch
from odoo.tools import replace_exceptions, str2bool

from odoo.addons.web.controllers.utils import ensure_db

_logger = logging.getLogger(__name__)
_f2qs_logger = _logger.getChild('test_fragment_to_query_string')


CT_JSON = {'Content-Type': 'application/json; charset=utf-8'}
WSGI_SAFE_KEYS = {'PATH_INFO', 'QUERY_STRING', 'RAW_URI', 'SCRIPT_NAME', 'wsgi.url_scheme'}


# Force concurrency errors. Patched in some tests.
should_fail = None


class TestHttp(http.Controller):
    def _readonly(self, rule, args):
        return str2bool(request.httprequest.args.get('readonly', True))

    def _max_content_length_1kiB(self):
        return 1024

    # =====================================================
    # Greeting
    # =====================================================

    @http.route(('/test_http/greeting', '/test_http/greeting-none'), type='http', auth='none')
    def greeting_none(self):
        return "Tek'ma'te"

    @http.route('/test_http/greeting-public', type='http', auth='public', readonly=_readonly)
    def greeting_public(self, readonly=True):
        assert self.env.user, "ORM should be initialized"
        assert self.env.cr.readonly == str2bool(readonly)
        return "Tek'ma'te"

    @http.route('/test_http/greeting-user', type='http', auth='user', readonly=_readonly)
    def greeting_user(self, readonly=True):
        assert self.env.user, "ORM should be initialized"
        assert self.env.cr.readonly == str2bool(readonly)
        return "Tek'ma'te"

    @http.route('/test_http/greeting-bearer', type='http', auth='bearer', bearer_scope='rpc', readonly=_readonly)
    def greeting_bearer(self, readonly=True):
        assert self.env.user, "ORM should be initialized"
        assert self.env.cr.readonly == str2bool(readonly)
        return f"Tek'ma'te; user={self.env.user.login}"

    @http.route('/test_http/greeting-bearer-other-scope', type='http', auth='bearer', bearer_scope='other_scope', readonly=True)
    def greeting_bearer_other_scope(self):
        return f"Tek'ma'te; user={self.env.user.login}"

    @http.route('/test_http/wsgi_environ', type='http', auth='none')
    def wsgi_environ(self):
        _logger.debug("Full WSGI environ:\n%s", pprint.pformat(request.httprequest.environ))
        environ = {
            key: val for key, val in request.httprequest.environ.items()
            if (key.startswith(('HTTP_', 'REMOTE_', 'REQUEST_', 'SERVER_', 'werkzeug.proxy_fix.')) or key in WSGI_SAFE_KEYS)
        }

        return request.make_response(
            json.dumps(environ, indent=4),
            headers=list(CT_JSON.items()),
        )

    @http.route('/test_http/raise-exception', type='http', auth='public')
    def raise_exception(self):
        raise Exception('Exception in logic')  # noqa: TRY002, EM101

    @http.route('/test_http/trigger-retrying', type='http', auth='public')
    def trigger_retrying(self):
        sf = SerializationFailure()
        sf.__setstate__({'pgcode': SERIALIZATION_FAILURE})
        raise sf

    # =====================================================
    # Echo-Reply
    # =====================================================
    @http.route('/test_http/echo-http-get', type='http', auth='none', methods=['GET'])
    def echo_http_get(self, **kwargs):
        return str(kwargs)

    @http.route('/test_http/echo-http-post', type='http', auth='none', methods=['POST'], csrf=False)
    def echo_http_post(self, **kwargs):
        return str(kwargs)

    @http.route('/test_http/echo-http-csrf', type='http', auth='none', methods=['POST'], csrf=True)
    def echo_http_csrf(self, **kwargs):
        return str(kwargs)

    @http.route('/test_http/echo-http-context-lang', type='http', auth='public', methods=['GET'], csrf=False)
    def echo_http_context_lang(self, **kwargs):
        return self.env.context.get('lang', '')

    @http.route('/test_http/echo-json', type='jsonrpc', auth='none', methods=['POST'], csrf=False)
    def echo_json(self, **kwargs):
        return kwargs

    @http.route('/test_http/echo-json-context', type='jsonrpc', auth='user', methods=['POST'], csrf=False, readonly=True)
    def echo_json_context(self, **kwargs):
        return self.env.context

    @http.route('/test_http/echo-json-over-http', type='http', auth='none', methods=['POST'], csrf=False)
    def echo_json_over_http(self):
        try:
            data = request.get_json_data()
        except ValueError as exc:
            e = "Invalid JSON data"
            raise werkzeug.exceptions.BadRequest(e) from exc
        return request.make_json_response(data)

    @http.route('/test_http/echo-json-null', type='jsonrpc', auth='none', readonly=True)
    def echo_json_null(self):
        return

    # =====================================================
    # Models
    # =====================================================
    @http.route('/test_http/<model("test_http.galaxy"):galaxy>', auth='public', readonly=True)
    def galaxy(self, galaxy):
        if not galaxy.exists():
            e = "The Ancients did not settle there."
            raise UserError(e)

        return http.request.render('test_http.tmpl_galaxy', {
            'galaxy': galaxy,
            'stargates': http.request.env['test_http.stargate'].search([
                ('galaxy_id', '=', galaxy.id),
            ]),
        })

    @http.route('/test_http/<model("test_http.galaxy"):galaxy>/setname',
                methods=['GET', 'POST'], type='http', auth='user', readonly=_readonly,
                max_content_length=_max_content_length_1kiB)
    def galaxy_set_name(self, galaxy, name, readonly=True):
        galaxy.name = name
        return galaxy.name

    @http.route('/test_http/<model("test_http.galaxy"):galaxy>/<model("test_http.stargate"):gate>', auth='user', readonly=True)
    def stargate(self, galaxy, gate):
        if not gate.exists():
            e = "The goauld destroyed the gate"
            raise UserError(e)

        return http.request.render('test_http.tmpl_stargate', {
            'gate': gate
        })

    # =====================================================
    # Cors
    # =====================================================
    @http.route('/test_http/cors_http_default', type='http', auth='none', cors='*')
    def cors_http(self):
        return "Hello"

    @http.route('/test_http/cors_http_methods', type='http', auth='none', methods=('GET', 'PUT'), cors='*')
    def cors_http_verbs(self, **kwargs):
        return "Hello"

    @http.route('/test_http/cors_http_auth', type="http", auth="thing", methods=('GET', 'OPTIONS'), cors="*")
    def cors_http_auth(self):
        raise "Hello"

    @http.route('/test_http/cors_json', type='jsonrpc', auth='none', cors='*')
    def cors_json(self, **kwargs):
        return {}

    @http.route('/test_http/cors_json_auth', type="jsonrpc", auth="thing", cors="*")
    def cors_json_auth(self):
        raise {}

    # =====================================================
    # Dual nodb/db
    # =====================================================
    @http.route('/test_http/ensure_db', type='http', auth='none')
    def ensure_db_endpoint(self, db=None):
        ensure_db()
        assert request.db, "There should be a database"
        return request.db

    # =====================================================
    # Session
    # =====================================================
    @http.route('/test_http/geoip', type='http', auth='none')
    def geoip(self):
        return json.dumps({
            'city': request.geoip.city.name,
            'country_code': request.geoip.country.iso_code or request.geoip.continent.code,
            'country_name': request.geoip.country.name or request.geoip.continent.name,
            'latitude': request.geoip.location.latitude,
            'longitude': request.geoip.location.longitude,
            'region': request.geoip.subdivisions[0].iso_code if request.geoip.subdivisions else None,
            'time_zone': request.geoip.location.time_zone,
        })

    @http.route('/test_http/save_session', type='http', auth='none')
    def touch(self):
        touch(request.session)
        return ''

    @http.route('/test_http/no_save_session', type='http', auth='none', save_session=False)
    def no_touch(self):
        touch(request.session)
        return ''

    # =====================================================
    # Errors
    # =====================================================
    @http.route('/test_http/fail', type='http', auth='none')
    def fail(self):
        _logger.error(
            "The /test_http/fail route should never be called, referrer: %s",
            http.request.httprequest.headers.get('referer')
        )
        raise request.not_found()

    @http.route('/test_http/json_value_error', type='jsonrpc', auth='none')
    def json_value_error(self):
        e = "Unknown destination"
        raise ValueError(e)

    @http.route('/test_http/hide_errors/decorator', type='http', auth='none')
    @replace_exceptions(AccessError, by=werkzeug.exceptions.NotFound())
    def hide_errors_decorator(self, error):
        if error == 'AccessError':
            e = "Wrong iris code"
            raise AccessError(e)
        if error == 'UserError':
            e = "Walter is AFK"
            raise UserError(e)

    @http.route('/test_http/hide_errors/context-manager', type='http', auth='none')
    def hide_errors_context_manager(self, error):
        with replace_exceptions(AccessError, by=werkzeug.exceptions.NotFound()):
            if error == 'AccessError':
                e = "Wrong iris code"
                raise AccessError(e)
            if error == 'UserError':
                e = "Walter is AFK"
                raise UserError(e)

    @http.route("/test_http/upload_file", methods=["POST"], type="http", auth="none", csrf=False)
    def upload_file_retry(self, ufile):
        global should_fail  # pylint: disable=W0603  # noqa: PLW0603
        if should_fail is None:
            e = f"The {(__name__ + '.should_fail')!r} global variable must be set."
            raise ValueError(e)

        data = ufile.read()
        if should_fail:
            should_fail = False  # Fail once
            sf = SerializationFailure()
            sf.__setstate__({'pgcode': SERIALIZATION_FAILURE})
            raise sf

        return data.decode()

    @http.route('/test_http/concurrency_error', type='http', auth='none')
    def concurrency_error(self):
        global should_fail  # noqa: PLW0603
        if should_fail is None:
            e = "should_fail must be set."
            raise ValueError(e)

        if should_fail:
            should_fail = False  # Fail once
            e = "A dummy concurrency error occurred"
            raise ConcurrencyError(e)

        return ''

    # =====================================================
    # Security
    # =====================================================
    @http.route('/test_http/httprequest_attrs', type='http', auth='none')
    def request_attrs(self):
        return json.dumps(dir(request.httprequest))

    @http.route('/test_http/httprequest_environ', type='http', auth='none')
    def request_environ(self):
        return json.dumps(list(request.httprequest.environ.keys()))

    # =====================================================
    # fragment to query string
    # =====================================================
    @http.route('/test_http/f2qs/testing-api')
    @fragment_to_query_string
    def f2qs_testing_api(self, **kwargs):
        return request.make_json_response(kwargs)

    @http.route('/test_http/f2qs/step1/no-operation-to-perform', type='http', auth='none')
    @fragment_to_query_string
    def f2qs_test(self, **kwargs):
        assert kwargs['race'] == 'Asgard', (
            "?race=Asgard was ok, fragment_to_query_string shouldnt intervene!"
        )
        _f2qs_logger.info("step 1: passed")
        step2 = '/test_http/f2qs/step2/1-var-in-fragment#race=Asgard'
        return request.redirect(step2)

    @http.route('/test_http/f2qs/step2/1-var-in-fragment', type='http', auth='none')
    @fragment_to_query_string
    def f2qs_test_simple_fragment(self, **kwargs):
        assert kwargs['race'] == 'Asgard', (
            'fragment_to_query_string should transform #race=Asgard into ?race=Asgard'
        )
        _f2qs_logger.info("step 2: passed")
        # go to step 3 of test
        step3 = '/test_http/f2qs/step3/3-var-in-fragment#race=Asgard&name=Thor&place=Orilla'
        return request.redirect(step3)

    @http.route('/test_http/f2qs/step3/3-var-in-fragment', type='http', auth='none')
    @fragment_to_query_string
    def f2qs_test_3_args_fragment(self, **kwargs):
        assert (
            kwargs['race'] == 'Asgard'
            and kwargs['name'] == 'Thor'
            and kwargs['place'] == 'Orilla'
        ), (
            "#race=Asgard&name=Thor&place=Orilla "
            "should have been transformed into "
            "?race=Asgard&name=Thor&place=Orilla"
        )
        _f2qs_logger.info("step 3: passed")
        # go to step 4 of test
        step4 = (
            '/test_http/f2qs/step4/'
            'empty-query-3-var-in-frag?#race=Asgard&name=Thor&place=Orilla'
        )
        return request.redirect(step4)

    @http.route('/test_http/f2qs/step4/empty-query-3-var-in-frag', type='http', auth='none')
    @fragment_to_query_string
    def f2qs_test_empty_query_with_fragment(self, **kwargs):
        assert (
            kwargs['race'] == 'Asgard'
            and kwargs['name'] == 'Thor'
            and kwargs['place'] == 'Orilla'
        ), (
            "?#race=Asgard&name=Thor&place=Orilla "
            "should have been transformed into "
            "?race=Asgard&name=Thor&place=Orilla"
        )
        _f2qs_logger.info("step 4: passed")
        step5 = '/test_http/f2qs/step5/debug-in-query-1-var-in-frag?debug=1#race=Asgard'
        return request.redirect(step5)

    @http.route('/test_http/f2qs/step5/debug-in-query-1-var-in-frag', type='http', auth='none')
    @fragment_to_query_string
    def f2qs_test_debug_in_query_with_fragment(self, **kwargs):
        assert (
            kwargs['race'] == 'Asgard'
        ), (
            "?debug=1#race=Asgard "
            "should have been transformed into "
            "?race=Asgard"
        )
        _f2qs_logger.info("step 5: passed")
        step6 = '/test_http/f2qs/step6/ignore-in-query-1-var-in-frag?media=GNN#race=Asgard'
        return request.redirect(step6)

    @http.route('/test_http/f2qs/step6/ignore-in-query-1-var-in-frag', type='http', auth='none')
    @fragment_to_query_string(ignore={'media'})
    def f2qs_test_parameter_to_ignore_in_query_with_fragment(self, **kwargs):
        assert (
            kwargs['race'] == 'Asgard' and kwargs['media'] == 'GNN'
        ), (
            "?media=GNN#race=Asgard "
            "should have been transformed into "
            "?media=GNN&race=Asgard"
        )
        _f2qs_logger.info("step 6: passed")
        return ''  # The end
