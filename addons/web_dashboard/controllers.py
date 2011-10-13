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
    def content(self, request, widget_id):
        return WIDGET_CONTENT_PATTERN % request.session.model('res.widget').read(
            [int(widget_id)], ['content'], request.session.eval_context(request.context)
        )[0]
