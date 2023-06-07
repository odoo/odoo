# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging

import werkzeug
from psycopg2.errorcodes import SERIALIZATION_FAILURE
from psycopg2 import OperationalError

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.tools import replace_exceptions

from odoo.addons.web.controllers.utils import ensure_db

_logger = logging.getLogger(__name__)


CT_JSON = {'Content-Type': 'application/json; charset=utf-8'}
WSGI_SAFE_KEYS = {'PATH_INFO', 'QUERY_STRING', 'RAW_URI', 'SCRIPT_NAME', 'wsgi.url_scheme'}


# Force serialization errors. Patched in some tests.
should_fail = None


class SerializationFailureError(OperationalError):
    pgcode = SERIALIZATION_FAILURE


class TestHttp(http.Controller):

    # =====================================================
    # Greeting
    # =====================================================
    @http.route(['/test_http/greeting', '/test_http/greeting-none'], type='http', auth='none')
    def greeting_none(self):
        return "Tek'ma'te"

    @http.route('/test_http/greeting-public', type='http', auth='public')
    def greeting_public(self):
        assert request.env.user, "ORM should be initialized"
        return "Tek'ma'te"

    @http.route('/test_http/greeting-user', type='http', auth='user')
    def greeting_user(self):
        assert request.env.user, "ORM should be initialized"
        return "Tek'ma'te"

    @http.route('/test_http/wsgi_environ', type='http', auth='none')
    def wsgi_environ(self):
        environ = {
            key: val for key, val in request.httprequest.environ.items()
            if (key.startswith('HTTP_')  # headers
             or key.startswith('REMOTE_')
             or key.startswith('REQUEST_')
             or key.startswith('SERVER_')
             or key.startswith('werkzeug.proxy_fix.')
             or key in WSGI_SAFE_KEYS)
        }

        return request.make_response(
            json.dumps(environ, indent=4),
            headers=list(CT_JSON.items())
        )

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
        return request.env.context.get('lang', '')

    @http.route('/test_http/echo-json', type='json', auth='none', methods=['POST'], csrf=False)
    def echo_json(self, **kwargs):
        return kwargs

    @http.route('/test_http/echo-json-context', type='json', auth='user', methods=['POST'], csrf=False)
    def echo_json_context(self, **kwargs):
        return request.env.context

    @http.route('/test_http/echo-json-over-http', type='http', auth='none', methods=['POST'], csrf=False)
    def echo_json_over_http(self):
        try:
            data = request.get_json_data()
        except ValueError as exc:
            raise werkzeug.exceptions.BadRequest("Invalid JSON data") from exc
        return request.make_json_response(data)

    # =====================================================
    # Models
    # =====================================================
    @http.route('/test_http/<model("test_http.galaxy"):galaxy>', auth='public')
    def galaxy(self, galaxy):
        if not galaxy.exists():
            raise UserError('The Ancients did not settle there.')

        return http.request.render('test_http.tmpl_galaxy', {
            'galaxy': galaxy,
            'stargates': http.request.env['test_http.stargate'].search([
                ('galaxy_id', '=', galaxy.id)
            ]),
        })

    @http.route('/test_http/<model("test_http.galaxy"):galaxy>/<model("test_http.stargate"):gate>', auth='user')
    def stargate(self, galaxy, gate):
        if not gate.exists():
            raise UserError("The goa'uld destroyed the gate")

        return http.request.render('test_http.tmpl_stargate', {
            'gate': gate
        })

    # =====================================================
    # Cors
    # =====================================================
    @http.route('/test_http/cors_http_default', type='http', auth='none', cors='*')
    def cors_http(self):
        return "Hello"

    @http.route('/test_http/cors_http_methods', type='http', auth='none', methods=['GET', 'PUT'], cors='*')
    def cors_http_verbs(self, **kwargs):
        return "Hello"

    @http.route('/test_http/cors_json', type='json', auth='none', cors='*')
    def cors_json(self, **kwargs):
        return {}

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
        return str(request.geoip)

    @http.route('/test_http/save_session', type='http', auth='none')
    def touch(self):
        request.session.touch()
        return ''

    # =====================================================
    # Errors
    # =====================================================
    @http.route('/test_http/json_value_error', type='json', auth='none')
    def json_value_error(self):
        raise ValueError('Unknown destination')

    @http.route('/test_http/hide_errors/decorator', type='http', auth='none')
    @replace_exceptions(AccessError, by=werkzeug.exceptions.NotFound())
    def hide_errors_decorator(self, error):
        if error == 'AccessError':
            raise AccessError("Wrong iris code")
        if error == 'UserError':
            raise UserError("Walter is AFK")

    @http.route('/test_http/hide_errors/context-manager', type='http', auth='none')
    def hide_errors_context_manager(self, error):
        with replace_exceptions(AccessError, by=werkzeug.exceptions.NotFound()):
            if error == 'AccessError':
                raise AccessError("Wrong iris code")
            if error == 'UserError':
                raise UserError("Walter is AFK")

    @http.route("/test_http/upload_file", methods=["POST"], type="http", auth="none", csrf=False)
    def upload_file_retry(self, ufile):
        global should_fail  # pylint: disable=W0603
        if should_fail is None:
            raise ValueError("should_fail should be set.")

        data = ufile.read()
        if should_fail:
            should_fail = False  # Fail once
            raise SerializationFailureError()

        return data.decode()
