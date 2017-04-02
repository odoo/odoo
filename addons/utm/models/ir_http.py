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
        cookies_to_set = []
        for var, dummy, cook in request.env['utm.mixin'].tracking_fields():
            if var in request.params and request.httprequest.cookies.get(var) != request.params[var]:
                cookies_to_set.append((cook, request.params[var], cls.get_utm_domain_cookies()))

        response = super(IrHttp, cls)._dispatch()
        if isinstance(response, Exception):
            return response

        for cookie_to_set in cookies_to_set:
            response.set_cookie(cookie_to_set[0], cookie_to_set[1], domain=cookie_to_set[2])

        return response
