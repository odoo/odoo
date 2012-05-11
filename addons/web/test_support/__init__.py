# -*- coding: utf-8 -*-
import xmlrpclib
from ..common.openerplib.main import Connector

execute_map = {}

class TestConnector(Connector):
    def db_list_lang(self):
        return [('en_US', u'Test Language')]

    def common_authenticate(self, db, login, password, environment):
        return 87539319

    def common_login(self, db, login, password):
        return self.common_authenticate(db, login, password, {})

    def object_execute_kw(self, db, uid, password, model, method, args, kwargs):
        if model in execute_map and hasattr(execute_map[model], method):
            return getattr(execute_map[model], method)(*args, **kwargs)

        raise xmlrpclib.Fault({
            'model': model,
            'method': method,
            'args': args,
            'kwargs': kwargs
        }, '')

    def send(self, service_name, method, *args):
        method_name = '%s_%s' % (service_name, method)
        if hasattr(self, method_name):
            return getattr(self, method_name)(*args)

        raise xmlrpclib.Fault({
            'service': service_name,
            'method': method,
            'args': args
        }, '')
