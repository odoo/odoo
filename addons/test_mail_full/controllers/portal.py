from odoo import http
from odoo.http import request


class PortalTest(http.Controller):
    """Implements some test portal routes (ex.: for viewing a record)."""

    @http.route('/my/test_portal/<int:res_id>', type='http', auth='public', methods=['GET'])
    def test_portal_record_view(self, res_id, access_token=None, **kwargs):
        return request.make_response(f'Record view of test_portal {res_id} ({access_token}, {kwargs})')

    @http.route('/test_portal/public_type/<int:res_id>', type='http', auth='public', methods=['GET'])
    def test_public_record_view(self, res_id):
        return request.make_response(f'Testing public controller for {res_id}')
