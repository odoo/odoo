import logging
import secrets

from odoo import models, fields, api, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class ApiKeyAllowedIps(models.Model):
    _name = 'kw.api.key.allowed.ips'
    _description = 'ApiKeyAllowedIps'

    name = fields.Char(
        required=True, )
    ip = fields.Char(
        required=True, )


class ApiKey(models.Model):
    _name = 'kw.api.key'
    _description = 'API-key'

    name = fields.Char(
        required=True, )
    active = fields.Boolean(
        default=True, )
    code = fields.Char(
        required=True, )
    is_ip_required = fields.Boolean(
        default=True, )
    allowed_ip_ids = fields.Many2many(
        comodel_name='kw.api.key.allowed.ips', )
    api_key = fields.Char(
        readonly=True, )
    description = fields.Text()

    _sql_constraints = [
        ('api_key_uniq', 'UNIQUE(api_key)', _('API-key must be unique'))]

    @api.model
    def create(self, vals):
        vals['api_key'] = secrets.token_urlsafe(120)
        return super(ApiKey, self).create(vals)

    def update_api_key(self):
        self.ensure_one()
        self.api_key = secrets.token_urlsafe(120)

    @api.model
    def get_api_key(self):
        res = {'api_key_string': False, 'api_key': False,
               'allowed_api_key_ip': False, }
        try:
            res['api_key_string'] = \
                request.httprequest.headers.get('api_key')
            if not res['api_key_string']:
                res['api_key_string'] = \
                    request.httprequest.headers.get('Authorization')
            if res['api_key_string']:
                res['api_key_string'] = \
                    res['api_key_string'].replace('Bearer', '').strip()
            if res['api_key_string']:
                res['api_key'] = self.search(
                    [('api_key', '=', res['api_key_string'])], limit=1)
                if res['api_key']:
                    remote_addr = request.httprequest.environ[
                        'REMOTE_ADDR']
                    if not res['api_key'].is_ip_required:
                        res['allowed_api_key_ip'] = remote_addr
                    else:
                        if remote_addr in \
                                res['api_key'].allowed_ip_ids.mapped('ip'):
                            res['allowed_api_key_ip'] = remote_addr
                else:
                    res['api_key_string'] = ''

        except Exception as e:
            _logger.warning(e)

        return res
