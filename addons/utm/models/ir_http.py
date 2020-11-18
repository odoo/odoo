# -*- coding: utf-8 -*-
from odoo.http import request
from odoo import models
from odoo.addons.base.models.ir_http import COOKIES_MARKETING

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _forbidden_cookies(cls):
        result = super()._forbidden_cookies()
        choices = cls._chosen_cookie_types()
        if COOKIES_MARKETING in choices:
            tracking_fields = request.env['utm.mixin'].tracking_fields()
            tracking_cookies = {field[2] for field in tracking_fields}
            result -= tracking_cookies
        return result

    @classmethod
    def get_utm_domain_cookies(cls):
        return request.httprequest.host

    @classmethod
    def _set_utm(cls, response):
        if isinstance(response, Exception):
            return response

        domain = cls.get_utm_domain_cookies()
        forbidden_cookies = cls._forbidden_cookies()
        for var, dummy, cook in request.env['utm.mixin'].tracking_fields():
            if cook not in forbidden_cookies and var in request.params and request.httprequest.cookies.get(var) != request.params[var]:
                response.set_cookie(cook, request.params[var], domain=domain)
        return response

    @classmethod
    def _dispatch(cls):
        response = super(IrHttp, cls)._dispatch()
        return cls._set_utm(response)

    @classmethod
    def _handle_exception(cls, exc):
        response = super(IrHttp, cls)._handle_exception(exc)
        return cls._set_utm(response)
