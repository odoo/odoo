from odoo import http
from odoo.http import request
from odoo.libs.debug_log import DebugLog

from odoo.addons.account.controllers.download_docs import _get_headers

_debug = DebugLog(__name__)


class AccountReportController(http.Controller):
    @http.route(
        '/account/download_attachments/<models("ir.attachment"):attachments>',
        type="http",
        auth="user",
    )
    def download_report_attachments(self, attachments):
        _debug.pipeline(
            "route", handler="AccountReportController.download_report_attachments"
        )
        attachments.check_access("read")
        assert all(
            attachment.res_id and attachment.res_model == "res.partner"
            for attachment in attachments
        )
        if len(attachments) == 1:
            headers = _get_headers(
                attachments.name, attachments.mimetype, attachments.raw
            )
            return request.prepare_response(attachments.raw, headers)
        else:
            content = attachments._prepare_zip_from_attachments()
            headers = _get_headers("attachments.zip", "zip", content)
            return request.prepare_response(content, headers)
