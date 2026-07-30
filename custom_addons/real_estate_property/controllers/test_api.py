import json
from odoo import http
from odoo.http import request

class TestAPI(http.Controller):

    @http.route("/api/test", methods=["GET"], type="http", auth="none", csrf=False)
    def test_endpoint(self):
        args = request.httprequest.data.decode()
        vals = json.loads(args)
        print(vals)
