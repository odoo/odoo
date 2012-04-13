# -*- coding: utf-8 -*-
import logging
try:
    import openerp.addons.web.common.http as openerpweb
except ImportError:
    import web.common.http as openerpweb

class PointOfSaleController(openerpweb.Controller):
    _cp_path = '/pos'

    @openerpweb.jsonrequest
    def dispatch(self, request, iface, **kwargs):
        method = 'iface_%s' % iface
        return getattr(self, method)(request, **kwargs)

    def iface_light(self, request, status):
        return True

