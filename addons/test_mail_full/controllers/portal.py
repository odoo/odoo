from odoo import http
from odoo.http import request


class PortalTest(http.Controller):
    """Implements some test portal routes (ex.: for viewing a record)."""

    @http.route('/my/test_portal/<int:res_id>', type='http', auth='public', methods=['GET'])
    def test_portal_record_view(self, res_id, access_token=None, **kwargs):
        return request.make_response(f'Record view of test_portal {res_id} ({access_token}, {kwargs})')

    @http.route("/my/test_portal_records/<int:res_id>", type="http", auth="public", website=True)
    def test_portal_record_page(self, res_id, **kwargs):
        record = request.env["mail.test.portal"]._get_thread_with_access(res_id, **kwargs)
        values = {
            "object": record,
            "token": kwargs.get("token"),
            "hash": kwargs.get("hash"),
            "pid": kwargs.get("pid"),
        }
        return request.render("test_mail_full.test_portal_template", values)

    @http.route("/my/test_portal_rating_records/<int:res_id>", type="http", auth="public", website=True)
    def test_portal_rating_record_page(self, res_id, **kwargs):
        record = request.env["mail.test.rating"]._get_thread_with_access(res_id, **kwargs)
        values = {
            "display_rating": True,
            "hash": kwargs.get("hash"),
            "object": record,
            "pid": kwargs.get("pid"),
            "token": kwargs.get("token"),
        }
        return request.render("test_mail_full.test_portal_template", values)

    @http.route('/test_portal/public_type/<int:res_id>', type='http', auth='public', methods=['GET'])
    def test_public_record_view(self, res_id):
        return request.make_response(f'Testing public controller for {res_id}')
