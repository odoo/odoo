# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import hmac
import logging
import os
import time

from odoo import http
from odoo.http import request
from odoo.tools import consteq

_logger = logging.getLogger(__name__)

TOKEN_TTL_SECONDS = 12 * 60 * 60

MAESTRO_APP_INDEX = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'static', 'src', 'maestro_app', 'index.html')


class MaestroAppController(http.Controller):

    def _app_secret(self):
        return request.env['ir.config_parameter'].sudo().get_param(
            'hr_maestro_integration.app_secret')

    def _issue_token(self, employee):
        secret = self._app_secret()
        exp = int(time.time()) + TOKEN_TTL_SECONDS
        payload = f"{employee.id}.{exp}"
        sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return f"{payload}.{sig}"

    def _verify_token(self, token):
        secret = self._app_secret()
        if not secret or not token:
            return request.env['hr.employee']
        try:
            emp_id_s, exp_s, sig = token.split('.')
        except ValueError:
            return request.env['hr.employee']
        payload = f"{emp_id_s}.{exp_s}"
        expected_sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not consteq(expected_sig, sig) or int(exp_s) < time.time():
            return request.env['hr.employee']
        employee = request.env['hr.employee'].sudo().browse(int(emp_id_s))
        return employee if employee.exists() and employee.active else request.env['hr.employee']

    def _profile_payload(self, employee):
        return {
            'profile': employee.maestro_app_profile,
            'employee_name': employee.name,
            'job_title': employee.job_id.name or '',
        }

    @http.route('/maestro/app', type='http', auth='public', methods=['GET'], csrf=False)
    def maestro_app_index(self, **kwargs):
        with open(MAESTRO_APP_INDEX, 'r', encoding='utf-8') as f:
            html = f.read()
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])

    @http.route('/maestro/app/login', type='json', auth='public', methods=['POST'], csrf=False)
    def maestro_app_login(self, barcode=None, pin=None, **kwargs):
        if not self._app_secret():
            _logger.error('Maestro app: hr_maestro_integration.app_secret não configurado.')
            return {'error': 'not_configured'}
        if not barcode or not pin:
            return {'error': 'missing_credentials'}

        Employee = request.env['hr.employee'].sudo()
        employee = Employee.search([('barcode', '=', barcode), ('active', '=', True)], limit=1)
        if not employee:
            return {'error': 'invalid_credentials'}

        if employee._maestro_app_login_locked():
            return {'error': 'locked'}

        if not employee.pin or not consteq(employee.pin, pin):
            employee._maestro_app_register_login_failure()
            return {'error': 'invalid_credentials'}

        if not employee.maestro_app_profile:
            return {'error': 'no_profile_mapped'}

        employee._maestro_app_register_login_success()
        return dict(self._profile_payload(employee), token=self._issue_token(employee))

    @http.route('/maestro/app/me', type='json', auth='public', methods=['POST'], csrf=False)
    def maestro_app_me(self, token=None, **kwargs):
        employee = self._verify_token(token)
        if not employee:
            return {'error': 'invalid_token'}
        if not employee.maestro_app_profile:
            return {'error': 'no_profile_mapped'}
        return self._profile_payload(employee)
