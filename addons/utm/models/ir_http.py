# -*- coding: utf-8 -*-
from odoo.http import request
from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def get_utm_domain_cookies(cls):
        return request.httprequest.host

    @classmethod
    def _set_utm(cls, response):
        if isinstance(response, Exception):
            return response

        domain = cls.get_utm_domain_cookies()
        for var, dummy, cook in request.env['utm.mixin'].tracking_fields():
            if var in request.params and request.httprequest.cookies.get(var) != request.params[var]:
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
