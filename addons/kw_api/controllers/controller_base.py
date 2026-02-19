import datetime
import json
import logging
import math
from functools import wraps
from io import BytesIO
from werkzeug.wsgi import wrap_file
from psycopg2._psycopg import IntegrityError
from odoo import fields, _, http
from odoo.addons.kw_mixin.models.datetime_extract import (
    mining_date, mining_datetime, )
from odoo.http import request, Response, Dispatcher
from odoo.tools import date_utils

_logger = logging.getLogger(__name__)


# pylint: disable=R1710, redefined-outer-name
def default(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()


class KwApiError(Exception):
    @property
    def code(self):
        if len(self.args) > 1:
            return self.args[0]
        if self.args:
            return 'internal_error'
        return ''

    @property
    def user_message(self):
        if len(self.args) > 1:
            return self.args[1]
        if self.args:
            return self.args[0]
        return ''

    @property
    def debug_message(self):
        if len(self.args) > 2:
            return self.args[2]
        return ''


class KwApi:
    log = False
    code = 200
    cors = False
    error = ''
    token = None
    token_string = None
    api_key = None
    api_key_string = None
    allowed_api_key_ip = None
    paginate = False
    request_type = 'http'
    page_index = 0
    page_size = 100
    data = {}

    # pylint: disable=too-many-branches, too-many-statements,
    # redefined-outer-name
    def __init__(self, token=True, api_key=False, paginate=False,
                 get_json=True, cors=False, request_type='http',
                 logging_is_required=True):
        self.paginate = paginate
        self.get_json = get_json
        self.cors = cors
        self.request_type = request_type
        # _logger.info(dict(request.httprequest.environ.get('wsgi.input')))
        try:
            if logging_is_required:
                # it create if logging_enabled and logging_is_required
                self.log = request.env['kw.api.log'].sudo().create({
                    'method': request.httprequest.method,
                    'ip': request.httprequest.environ['REMOTE_ADDR'],
                    'name': request.httprequest.url,
                    'headers': request.httprequest.headers,
                    'json': request.httprequest.data,
                })
        except Exception as e:
            _logger.info('KwApi init: kw.api.log create Error: %s', e)
        else:
            # pylint: disable=E8102
            request._cr.commit()

        context = request.env.context.copy()

        update_lang = request.env['ir.config_parameter'].sudo(
        ).get_param(key='kw_api.kw_api_update_lang_param_name')

        lang = None
        if update_lang:
            lang = request.env['res.lang'].sudo().search([
                ('iso_code', '=',
                 request.httprequest.headers.get(update_lang, '')[:2])
            ], limit=1)
            if lang:
                context.update({'lang': lang.code})
        if token:
            try:
                self.token_string = \
                    request.httprequest.headers.get('access_token')
                if not self.token_string:
                    self.token_string = request.httprequest.headers.get(
                        'Authorization')
                if self.token_string:
                    self.token_string = \
                        self.token_string.replace('Bearer', '').strip()
                if self.token_string:
                    self.token = request.env['kw.api.token'].sudo().search(
                        [('name', '=', self.token_string)], limit=1)
                    if self.token:
                        if self.log:
                            self.log.login = self.token.user_id.login
                    else:
                        self.token_string = ''  # nosec B105
                    if self.token and self.token.is_expired:
                        self.token_string = False
                        # raise KwApiError('auth_error', 'Token is expired')
                    if self.token and self.token.user_id:
                        context.update({
                            'uid': self.token.user_id.id,
                            'partner_id': self.token.user_id.partner_id.id, })
                        lang_update = bool(
                            request.env['ir.config_parameter'].sudo(
                            ).get_param(
                                key='kw_api.kw_api_update_lang_from_header'))
                        if lang and lang_update and \
                                self.token.user_id.lang != lang.code:
                            self.token.user_id.lang = lang.code
                        request.env.user = self.token.user_id
            except Exception as e:
                _logger.warning(e)

        # pylint: disable=R1702
        if api_key:
            for k, v in request.env['kw.api.key'].sudo().get_api_key().items():
                setattr(self, k, v)
            if self.api_key and self.log:
                self.log.login = self.api_key.name
        request.env.context = context

    @staticmethod
    def options_response(**kw):
        _logger.debug(kw)
        response = Response(status=204, )
        response.headers.set('Access-Control-Allow-Origin', '*')
        response.headers.set(
            'Access-Control-Allow-Methods', 'GET, POST, PUT, OPTIONS')
        response.headers.set(
            'Access-Control-Allow-Headers',
            'Origin, X-Requested-With, Content-Type, Accept, '
            'X-Debug-Mode, access-token, authorization')
        return response

    def response(self, code=None, error=None, data=None, cors=None, ):
        error = error or self.error
        ensure_ascii = bool(request.env['ir.config_parameter'].sudo(
        ).get_param(key='kw_api.kw_api_ensure_ascii'))
        response = json.dumps(
            obj={'result': data}, default=default, ensure_ascii=False)
        if not ensure_ascii:
            response = response.encode('utf-8')
        code = code or self.code
        cors = cors or self.cors
        if self.log:
            if error:
                self.log.error = error
            self.log.response = response
            self.log.code = code
        if self.request_type == 'json':
            return data
        user_result_wrapper = bool(request.env['ir.config_parameter'].sudo(
        ).get_param(key='kw_api.kw_api_user_result_wrapper'))
        if user_result_wrapper:
            data = {'result': data}
        body = json.dumps(data, default=date_utils.json_default,
                          ensure_ascii=ensure_ascii)
        body = str.encode(body)
        buf = wrap_file(http.request.httprequest.environ, BytesIO(body))
        response = Response(buf, status=code, headers=[
            ('Content-Type', 'application/json'),
            ('Content-Length', len(body))])
        if cors:
            response.headers.set('Access-Control-Allow-Origin', '*')
            response.headers.set(
                'Access-Control-Allow-Methods', 'GET, POST, PUT, OPTIONS')
            response.headers.set(
                'Access-Control-Allow-Headers',
                'Origin, X-Requested-With, Content-Type, Accept, '
                'X-Debug-Mode, access-token, authorization')
        return response

    def err_response(self, code='', msg='', error=''):
        return self.response(
            code=400, error=error, data={'error': {
                'code': code, 'message': msg}}, )

    def err_response_kw_error(self, e):
        # _logger.info("----------------")
        # _logger.info(e)
        # _logger.info(e.args)
        debug_message = e.debug_message if hasattr(e, 'debug_message') \
            else e.args[0]
        user_message = e.user_message \
            if hasattr(e, 'user_message') else e.args[0]
        code = e.code if hasattr(e, 'code') else 'error'
        return self.response(
            code=400, error=debug_message, data={'error': {
                'code': code, 'message': user_message}}, )

    def ok_response(self, code='', msg='', ):
        return self.response(
            code=200, data={'code': code, 'message': msg}, )

    def data_response(self, data='', method='kw_api_get_data'):
        if not self.paginate:
            if hasattr(data, method):
                data = getattr(data, method)()
            return self.response(code=200, data=data)
        offset = self.page_size * self.page_index
        if not offset:
            offset = 0
        total_elements = len(data)
        total_pages = math.ceil(total_elements / self.page_size)
        if hasattr(data, 'search'):
            data = data.search([('id', 'in', data.ids)], offset=offset,
                               limit=self.page_size)
            if hasattr(data, method):
                data = getattr(data, method)()
            else:
                data = [{'id': obj.id} for obj in data]
        else:
            data = data[offset:offset + self.page_size]
        number_of_elements = len(data)
        paginated_data = {
            'content': data,
            'totalElements': total_elements,
            'totalPages': total_pages,
            'numberOfElements': number_of_elements,
            'number': self.page_index,
            'last': (total_pages - self.page_index) <= 0, }
        return self.response(code=200, data=paginated_data)

    @staticmethod
    def get_param_by_name(data, param, data_type=None, required_type=False):
        # data_type in ['int', 'str', 'date', 'datetime', 'float', 'bool']
        if param not in data:
            raise KwApiError(
                'data_error', '"{}" is missing'.format(param),
                '"{}" not in data'.format(param))
        if data_type == 'date':
            if not required_type and not data[param]:
                return False
            try:
                return mining_date(data[param])
            except Exception as e:
                raise KwApiError(
                    'data_error', '"{}" is not {}'.format(param, data_type), e)
        elif data_type == 'datetime':
            if not required_type and not data[param]:
                return False
            try:
                return mining_datetime(data[param])
            except Exception as e:
                raise KwApiError(
                    'data_error', '"{}" is not {}'.format(param, data_type), e)
        elif data_type and str(data_type.__name__) in ['int', 'str', 'float']:
            try:
                return data_type(data[param])
            except Exception as e:
                raise KwApiError(
                    'data_error', '"{}" is not {}'.format(param, data_type), e)
        return data[param]

    def get_data_param_by_name(self, param, data_type=None):
        return self.get_param_by_name(self.data, param, data_type)

    def get_fields_by_name(self, data, field_list):
        # fields = [
        #   ('model_field_name', 'api_param', type),
        # ]
        result = {}
        for obj in field_list:
            if obj[1] in data:
                if len(obj) > 2:
                    result[obj[0]] = \
                        self.get_param_by_name(data, obj[1], obj[2])
                else:
                    result[obj[0]] = self.get_param_by_name(data, obj[1])
        return result

    def get_data_fields_by_name(self, field_list):
        return self.get_fields_by_name(self.data, field_list)

    @staticmethod
    def remove_unchanged_param(obj, data, field_list=None):
        result = {}
        if not field_list:
            field_list = list(data.keys())
        for f in field_list:
            if hasattr(obj, f) and f in data:
                x2many_cls = (fields.Many2many, fields.One2many)
                if isinstance(obj._fields.get(f), x2many_cls):
                    # _logger.info(data[f])
                    if getattr(obj, f).ids != data[f]:
                        result[f] = [(6, 0, data[f])]
                    continue
                # x2many_cls = (fields.Many2one,)
                if isinstance(obj._fields.get(f), fields.Many2one):
                    if hasattr(getattr(obj, f), 'id'):
                        if getattr(obj, f).id != data[f]:
                            result[f] = data[f]
                    else:
                        if getattr(obj, f) != data[f]:
                            result[f] = data[f]
                    continue
                date_cls = ['date', 'datetime', ]
                if str(type(getattr(obj, f)).__name__) in date_cls:
                    if str(data[f]) != str(getattr(obj, f)):
                        result[f] = data[f]
                elif data[f] != getattr(obj, f):
                    result[f] = data[f]
        return result

    def list_response(self, records, **kw):
        if len(records):
            return self.data_response(records)
        return self.data_response(records.kw_api_search(**kw))

    def get_response(self, records, obj_id, **kw):
        obj_id = records.search([('id', '=', obj_id), ], limit=1)
        if not obj_id:
            raise KwApiError('Data error', 'Wrong ID')
        return self.data_response(obj_id.kw_api_get_record_value())

    def create_response(self, records, **kw):
        data = self.get_data_fields_by_name(records.kw_api_fields())
        obj_id = records.create(data)
        return self.data_response(obj_id.kw_api_get_record_value())

    def update_response(self, records, obj_id=None, **kw):
        obj_id = records.search([('id', '=', obj_id), ], limit=1)
        if not obj_id:
            raise KwApiError('Data error', 'Wrong ID')
        data = self.get_data_fields_by_name(records.kw_api_fields())
        obj_id.write(data)
        return self.data_response(obj_id.kw_api_get_record_value())


# pylint: disable=too-many-return-statements
def kw_api_wrapper(token=True, api_key=False, paginate=False, get_json=True,
                   cors=False, request_type='http', ):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            kw_api = KwApi(token=token, api_key=api_key, paginate=paginate,
                           get_json=get_json, cors=cors,
                           request_type=request_type)
            if kw_api.log:
                kw_api.log.post = json.dumps(
                    obj=kwargs, default=default, ensure_ascii=False)

            if token and not kw_api.token_string:
                # return kw_api.err_response(
                #     'auth_error',
                #     _('No token were given or given wrong one'),
                #     'not token or wrong')
                return kw_api.response(
                    code=401, error='not token or wrong', data={
                        'code': 'auth_error', 'message': _(
                            'No token were given or given wrong one')}, )
            if api_key and not kw_api.allowed_api_key_ip:
                return kw_api.response(
                    code=401, error='not api-key or wrong or not allowed ip',
                    data={'code': 'auth_error',
                          'message': _(
                              'No API-key were given or given wrong one '
                              'or not allowed request source ip')}, )

            if kw_api.paginate:
                try:
                    page = kw_api.get_fields_by_name(kwargs, [
                        ('index', 'pageIndex', int),
                        ('size', 'pageSize', int), ])
                    kw_api.page_index = page.get('index', kw_api.page_index)
                    kw_api.page_size = page.get('size', kw_api.page_size)
                except Exception as e:
                    return kw_api.err_response_kw_error(e)

            if kw_api.get_json:
                try:
                    kw_api.data = json.loads(
                        request.httprequest.data.decode('utf-8'))
                except Exception as e:
                    return kw_api.err_response(
                        'request_error', 'JSON is invalid', e)
            try:
                return func(kw_api=kw_api, *args, **kwargs)
            except IntegrityError as e:
                # can't use the usual `http.request.env.cr` style,
                # because `env` queries db and everything explodes
                http.request._cr.rollback()
                return kw_api.err_response_kw_error(e)
            except Exception as e:
                _logger.warning(e)
                # raise e  # uncomment for local debug
                return kw_api.err_response_kw_error(e)

        wrapper.original_func = func
        return wrapper

    return decorator


def kw_api_route(route=None, **kw):
    routing = kw.copy()
    routing['kw_type'] = kw.get('type', 'http')
    routing['type'] = 'kw_api'
    routing['auth'] = kw.get('type', 'public')
    routing['website'] = False
    routing['csrf'] = False
    return http.route(route=route, **routing)


class KwApiDispatcher(Dispatcher):
    routing_type = 'kw_api'

    @classmethod
    def is_compatible_with(cls, request):
        return True

    def dispatch(self, endpoint, args):
        self.request.params = dict(request.httprequest.args)
        jsonrequest = json.loads(
            self.request.httprequest.get_data(as_text=True) or '{}')
        self.request.params.update(dict(jsonrequest.get('params', {}), **args))

        return endpoint(**self.request.params)

    def handle_error(self, exc):
        self.request.make_json_response({'error': exc})
