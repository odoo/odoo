# -*- coding: utf-8 -*-
try:
    import openerp.addons.web.common.http as openerpweb
except ImportError:
    import web.common.http as openerpweb

class Widgets(openerpweb.Controller):
    _cp_path = '/web_graph/graph'

    @openerpweb.jsonrequest
    def data_get(self, req, domain=[], context={}, group_by=[], view_id=False, orientation=False, **kwargs):
        print '---'
        print req
        print domain
        print context
        print group_by
        return [{'hello': 3}]
