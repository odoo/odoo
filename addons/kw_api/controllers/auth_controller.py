import logging

import odoo
from odoo import http, _
from odoo.http import request

from .controller_base import kw_api_wrapper, KwApiError, kw_api_route

_logger = logging.getLogger(__name__)


class AuthController(http.Controller):

    @kw_api_route(
        route=['/kw_api/auth/token'], methods=['POST'], )
    @kw_api_wrapper(token=False, paginate=False, get_json=True, )
    def kw_api_auth_token_post(self, kw_api, **kw):
        login = kw_api.get_data_param_by_name('login', str)
        user = request.env['res.users'].sudo().search([
            ('login', '=', login)], limit=1)
        if not user:
            raise KwApiError('auth_error', 'Wrong login / password',
                             'wrong login {}'.format(login))
        password = kw_api.get_data_param_by_name('password', str)
        db = request.env.cr.dbname
        try:
            request.env['res.users'].sudo().check(db, user.id, password)
        except Exception as e:
            raise KwApiError('auth_error', 'Wrong phone / password', e)
        env = odoo.api.Environment(
            request.env.cr, user.id, request.env.context)
        env['res.users.log'].create({})
        token = request.env['kw.api.token'].sudo().create({'user_id': user.id})
        return kw_api.data_response(token.kw_api_get_data())

    @kw_api_route(route='/kw_api/auth/token/refresh', methods=['POST'], )
    @kw_api_wrapper(token=False, paginate=False, get_json=True, )
    def kw_api_auth_token_refresh_post(self, kw_api, **kw):
        token = kw_api.get_data_param_by_name('refreshToken', str)
        token = request.env['kw.api.token'].refresh_token_by_refresh_token(
            token)
        if token.is_refresh_token_expired:
            raise KwApiError(
                'auth_error', _('No token were given or given wrong one'),
                'refresh_token_expired')
        return kw_api.data_response(token.kw_api_get_data())

    @kw_api_route(route='/kw_api/auth/token', methods=['DELETE'], )
    @kw_api_wrapper(token=False, paginate=False, get_json=True, )
    def kw_api_auth_token_delete(self, kw_api, **kw):
        kw_api.token.unlink()
        return kw_api.ok_response(
            message=_('Token has been successfully deleted'))
