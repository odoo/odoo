# -*- coding: utf-8 -*-
from odoo.http import request
from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def get_utm_domain_cookies(cls):
        return request.httprequest.host

    @classmethod
    def _dispatch(cls):
        response = super(IrHttp, cls)._dispatch()
        if isinstance(response, Exception):
            return response
        for var, dummy, cook in request.env['utm.mixin'].tracking_fields():
            if var in request.params and request.httprequest.cookies.get(var) != request.params[var]:
                response.set_cookie(cook, request.params[var], domain=cls.get_utm_domain_cookies())
        return response
