import werkzeug.exceptions
import odoo.exceptions
from odoo.http import Controller, route


class TestExceptionsController(Controller):
    @route([
        '/test_exceptions/http/400',
        '/test_exceptions/http/BadRequest',
        '/test_exceptions/http/bad_request',
    ], type='http', auth='none')
    def bad_request_http(self):
        raise werkzeug.exceptions.BadRequest("Custom bad request message")

    @route([
        '/test_exceptions/json/400',
        '/test_exceptions/json/BadRequest',
        '/test_exceptions/json/bad_request',
    ], type='json', auth='none')
    def bad_request_json(self):
        raise werkzeug.exceptions.BadRequest("Custom bad request message")

    @route([
        '/test_exceptions/http/401',
        '/test_exceptions/http/Unauthorized',
        '/test_exceptions/http/unauthorized',
    ], type='http', auth='none')
    def unauthorized_http(self):
        raise werkzeug.exceptions.Unauthorized("Custom unauthorized message")

    @route([
        '/test_exceptions/json/401',
        '/test_exceptions/json/Unauthorized',
        '/test_exceptions/json/unauthorized',
    ], type='json', auth='none')
    def unauthorized_json(self):
        raise werkzeug.exceptions.Unauthorized("Custom unauthorized message")

    @route([
        '/test_exceptions/http/403',
        '/test_exceptions/http/Forbidden',
        '/test_exceptions/http/forbidden',
    ], type='http', auth='none')
    def forbidden_http(self):
        raise werkzeug.exceptions.Forbidden("Custom forbidden message")

    @route([
        '/test_exceptions/json/403',
        '/test_exceptions/json/Forbidden',
        '/test_exceptions/json/forbidden'
    ], type='json', auth='none')
    def forbidden_json(self):
        raise werkzeug.exceptions.Forbidden("Custom forbidden message")

    @route([
        '/test_exceptions/http/404',
        '/test_exceptions/http/NotFound',
        '/test_exceptions/http/not_found',
    ], type='http', auth='none')
    def not_found_http(self):
        raise werkzeug.exceptions.NotFound("Custom not found message")

    @route([
        '/test_exceptions/json/404',
        '/test_exceptions/json/NotFound',
        '/test_exceptions/json/not_found',
    ], type='json', auth='none')
    def not_found_json(self):
        raise werkzeug.exceptions.NotFound("Custom not found message")

    @route([
        '/test_exceptions/http/UserError',
        '/test_exceptions/http/user_error',
    ], type='http', auth='none')
    def user_error_http(self):
        raise odoo.exceptions.UserError("Custom user error message")

    @route([
        '/test_exceptions/json/UserError',
        '/test_exceptions/json/user_error',
    ], type='json', auth='none')
    def user_error_json(self):
        raise odoo.exceptions.UserError("Custom user error message")

    @route([
        '/test_exceptions/http/AccessDenied',
        '/test_exceptions/http/access_denied',
    ], type='http', auth='none')
    def access_denied_http(self):
        raise odoo.exceptions.AccessDenied()

    @route([
        '/test_exceptions/json/AccessDenied',
        '/test_exceptions/json/access_denied',
    ], type='json', auth='none')
    def access_denied_json(self):
        raise odoo.exceptions.AccessDenied()

    @route([
        '/test_exceptions/http/AccessError',
        '/test_exceptions/http/access_error',
    ], type='http', auth='none')
    def access_error_http(self):
        raise odoo.exceptions.AccessError("Custom access error message")

    @route([
        '/test_exceptions/json/AccessError',
        '/test_exceptions/json/access_error',
    ], type='json', auth='none')
    def access_error_json(self):
        raise odoo.exceptions.AccessError("Custom access error message")

    @route([
        '/test_exceptions/http/MissingError',
        '/test_exceptions/http/missing_error',
    ], type='http', auth='none')
    def missing_error_http(self):
        raise odoo.exceptions.MissingError("Custom missing error message")

    @route([
        '/test_exceptions/json/MissingError',
        '/test_exceptions/json/missing_error',
    ], type='json', auth='none')
    def missing_error_json(self):
        raise odoo.exceptions.MissingError("Custom missing error message")

    @route([
        '/test_exceptions/http/ValidationError',
        '/test_exceptions/http/validation_error',
    ], type='http', auth='none')
    def validation_error_http(self):
        raise odoo.exceptions.ValidationError("Custom validation error message")

    @route([
        '/test_exceptions/json/ValidationError',
        '/test_exceptions/json/validation_error',
    ], type='json', auth='none')
    def validation_error_json(self):
        raise odoo.exceptions.ValidationError("Custom validation error message")
