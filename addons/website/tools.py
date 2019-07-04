# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
import werkzeug

from odoo.tools import DotDict


class MockObject(object):
    _log_call = []

    def __init__(self, *args, **kwargs):
        self.__dict__ = kwargs

    def __call__(self, *args, **kwargs):
        self._log_call.append((args, kwargs))
        return self

    def __getitem__(self, index):
        return self


def werkzeugRaiseNotFound(*args, **kwargs):
    raise werkzeug.exceptions.NotFound()


class MockRequest(object):
    """ Class with context manager mocking odoo.http.request for tests """
    def __init__(self, env, **kw):
        app = MockObject(routing={
            'type': 'http',
            'website': True,
            'multilang': kw.get('multilang', True),
        })
        app.get_db_router = app.bind = app.match = app
        if not kw.get('routing', True):
            app.match = werkzeugRaiseNotFound
        self.request = DotDict({
            'context': kw.get('context', {}),
            'db': None,
            'debug': False,
            'env': env,
            'httprequest': {
                'path': '/hello/',
                'app': app,
            },
            'redirect': werkzeug.utils.redirect,
            'session': {
                'geoip': {
                    'country_code': kw.get('country_code'),
                },
                'sale_order_id': kw.get('sale_order_id'),
            },
            'website': kw.get('website'),
        })
        odoo.http._request_stack.push(self.request)

    def __enter__(self):
        return self.request

    def __exit__(self, exc_type, exc_value, traceback):
        odoo.http._request_stack.pop()
