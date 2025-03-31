import json

from odoo import http
from odoo.http import request


class TestsSharedJsPython(http.Controller):

    @http.route('/account/init_tests_shared_js_python', type='http', auth='user', website=True)
    def route_init_tests_shared_js_python(self):
        tests = json.loads(request.env['ir.config_parameter'].get_param('account.tests_shared_js_python', '[]'))
        return request.render('account.tests_shared_js_python', {'props': {'tests': tests}})

    @http.route('/account/post_tests_shared_js_python', type='json', auth='user')
    def route_post_tests_shared_js_python(self, results):
        request.env['ir.config_parameter'].set_param('account.tests_shared_js_python', json.dumps(results or []))
