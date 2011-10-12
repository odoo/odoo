# -*- coding: utf-8 -*-
import web.common.http as openerpweb

WIDGET_CONTENT_PATTERN = """<!DOCTYPE html>
<html>
    <head><title>[[Widget %(id)d]]</title></head>
    <body>
        %(content)s
        <script type="text/javascript">
            var load = window.onload;
            window.onload = function () {
                if (load) {
                    load();
                }
                window.frameElement.style.height = document.height + 'px';
            }
        </script>
    </body>
</html>
"""
class Widgets(openerpweb.Controller):
    _cp_path = '/web_dashboard/widgets'

    @openerpweb.httprequest
    def content(self, req, widget_id):
        Widget = req.session.model('res.widget')
        w = Widget.read([widget_id], ['content'], req.session.eval_context(req.context))
        if w:
            r = WIDGET_CONTENT_PATTERN % w[0]
        else:
            r = "Widget unavailable"
        return r
