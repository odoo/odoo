# -*- coding: utf-8 -*-
import logging
import simplejson

from openerp.addons.web.controllers.main import DataSet
from openerp import http
from openerp.http import request

_logger = logging.getLogger(__name__)

class RequestCacheController(DataSet):

    def get_data(self, model, *args):

        self.hashkey = request.env['cache.store'].get_hash(model, model, args)

        if not hasattr(request.env[model], '_cache_dependencies'):
            return False

        return request.env['cache.store'].get(self.hashkey)


    @http.route('/web/dataset/call_kw_cache', type='json', auth='user')
    def call_kw_cache(self, model, method, args, kwargs):
        result = self.get_data(model, method, args, kwargs)
        if result:
            return simplejson.loads(result)

        result = self._call_kw(model, method, args, kwargs)
        request.env['cache.store'].archive(self.hashkey, model, result)
        return  result

    @http.route('/web/dataset/search_read_cache', type='json', auth='user')
    def search_read_cache(self, model, fields=False, offset=0, limit=False, domain=None, sort=None):
        result = self.get_data(model, fields, offset, limit, domain, sort)
        if result:
            return simplejson.loads(result)

        result = self.do_search_read(model, fields, offset, limit, domain, sort)
        request.env['cache.store'].archive(self.hashkey, model, result)
        return  result