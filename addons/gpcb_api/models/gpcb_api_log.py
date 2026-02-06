# Part of GPCB. See LICENSE file for full copyright and licensing details.

import json
import logging
import time

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class GpcbApiLog(models.Model):
    _name = 'gpcb.api.log'
    _description = 'API Request/Response Log'
    _order = 'create_date desc'
    _log_access = True

    endpoint = fields.Char(string='Endpoint', required=True, index=True)
    method = fields.Char(string='HTTP Method', required=True)
    user_id = fields.Many2one('res.users', string='API User', index=True)
    request_body = fields.Text(string='Request Body')
    response_body = fields.Text(string='Response Body')
    status_code = fields.Integer(string='HTTP Status')
    duration_ms = fields.Float(string='Duration (ms)')
    ip_address = fields.Char(string='IP Address')
    error_message = fields.Text(string='Error')

    @api.autovacuum
    def _gc_old_logs(self):
        """Remove API logs older than 90 days."""
        limit_date = fields.Datetime.subtract(fields.Datetime.now(), days=90)
        self.sudo().search([('create_date', '<', limit_date)]).unlink()
        _logger.info('Cleaned up API logs older than %s', limit_date)


class GpcbApiLogMixin:
    """Mixin providing API logging helpers for controllers."""

    def _log_api_call(self, env, endpoint, method, request_data=None,
                      response_data=None, status_code=200, duration_ms=0,
                      ip_address='', error=None):
        """Create an audit log entry for an API call."""
        try:
            env['gpcb.api.log'].sudo().create({
                'endpoint': endpoint,
                'method': method,
                'user_id': env.uid,
                'request_body': json.dumps(request_data, default=str)[:10000] if request_data else '',
                'response_body': json.dumps(response_data, default=str)[:10000] if response_data else '',
                'status_code': status_code,
                'duration_ms': duration_ms,
                'ip_address': ip_address or '',
                'error_message': str(error)[:5000] if error else '',
            })
        except Exception:
            _logger.warning('Failed to log API call to %s', endpoint, exc_info=True)

    def _api_success(self, data=None, message='Success', status=200):
        """Standard success response."""
        return {'status': 'success', 'message': message, 'data': data or {}}, status

    def _api_error(self, message, status=400, details=None):
        """Standard error response."""
        result = {'status': 'error', 'message': message}
        if details:
            result['details'] = details
        return result, status
