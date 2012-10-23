# -*- coding: utf-8 -*-
import openerp

from lxml import etree

class GraphView(openerp.addons.web.controllers.main.View):
    _cp_path = '/web_graph/graph'

    @openerp.addons.web.http.jsonrequest
    def data_get(self, req, model=None, domain=[], context={}, group_by=[], view_id=False, orientation=False, stacked=False, mode="bar", **kwargs):
        pass

