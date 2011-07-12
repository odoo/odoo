# -*- coding: utf-8 -*-
import openerpweb

class Widgets(openerpweb.openerpweb.Controller):
    _cp_path = '/base_dashboard/widgets'

    @openerpweb.httprequest
    def content(self, request, widget_id):
        return request.session.model('res.widget').read(
            [widget_id], ['content'], request.session.eval_context(request.context)
        )[0]['content']
