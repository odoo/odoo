# -*- coding: utf-8 -*-
from openerp import http

class {{ name|snake }}(http.Controller):
    @http.route('/{{ name|snake }}/{{ name|snake }}/', auth='public')
    def index(self, **kw):
        return "Hello, world"
