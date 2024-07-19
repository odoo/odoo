from odoo import http
from odoo.http import request, Response
import json

class MyController(http.Controller):
    @http.route('/api/test_json', type='json', auth='user', methods=['POST'])
    def test_json(self, **kwargs):
        try:
            print("Received data:", kwargs)
            return {'status': 'success', 'data': kwargs}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
