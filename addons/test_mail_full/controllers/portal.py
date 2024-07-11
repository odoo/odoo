# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import http
from odoo.http import request


class PortalTest(http.Controller):
    """Implements some test portal routes (ex.: for viewing a record)."""

    @http.route('/my/test_portal/<int:res_id>', type='http', auth='public', methods=['GET'])
    def test_portal_record_view(self, res_id, access_token=None, **kwargs):
        return request.make_response(f'Record view of test_portal {res_id} ({access_token}, {kwargs})')
