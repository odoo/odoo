import json
from types import GeneratorType

from odoo import http
from odoo.http import InternalServerError, prepare_content_disposition_header, request
from odoo.libs.debug_log import DebugLog
from odoo.tools.misc import html_escape

from odoo.addons.account.controllers.download_docs import _get_headers
from odoo.addons.account.models.account_report_engine import (
    AccountReportFileDownloadException,
)

_debug = DebugLog(__name__)


class AccountReportController(http.Controller):
    @http.route("/account_reports", type="http", auth="user", methods=["POST"])
    def get_report(self, options, file_generator, **kwargs):
        _debug.pipeline("route", handler="AccountReportController.get_report")
        uid = request.env.uid
        options = json.loads(options)

        allowed_company_ids = request.env["account.report"].get_report_company_ids(
            options
        )
        if not allowed_company_ids:
            # The cookie is client-controlled, so it may be anything; env.companies
            # rejects ids the user is not allowed, but only once it can parse them.
            company_str = request.cookies.get("cids") or ""
            allowed_company_ids = [
                int(str_id) for str_id in company_str.split("-") if str_id.isdigit()
            ] or request.env.user.company_id.ids

        report = (
            request.env["account.report"]
            .with_user(uid)
            .with_context(allowed_company_ids=allowed_company_ids)
            .browse(options["report_id"])
        )

        try:
            with _debug.perf(
                "get_report",
                cr=request.env.cr,
                report=report,
                file_generator=file_generator,
                companies=allowed_company_ids,
            ):
                generated_file_data = report.dispatch_report_action(
                    options, file_generator
                )
            file_content = generated_file_data["file_content"]
            file_type = generated_file_data["file_type"]
            response_headers = self._get_response_headers(
                file_type, generated_file_data["file_name"], file_content
            )

            if file_type == "xlsx":
                response = request.prepare_response(None, headers=response_headers)
                response.stream.write(file_content)
            else:
                response = request.prepare_response(
                    file_content, headers=response_headers
                )

            if file_type in ("zip", "xaf") or isinstance(file_content, GeneratorType):
                # Adding direct_passthrough to the response and giving it a file
                # as content means that we will stream the content of the file to the user
                # Which will prevent having the whole file in memory
                response.direct_passthrough = True

            return response
        except AccountReportFileDownloadException as e:
            if e.content:
                e.content["file_content"] = e.content["file_content"].decode()
            data = {
                "name": type(e).__name__,
                "arguments": [e.errors, e.content],
            }
            raise InternalServerError(response=self._generate_response(data)) from e
        except Exception as e:
            data = http.serialize_exception(e)
            raise InternalServerError(response=self._generate_response(data)) from e

    def _generate_response(self, data):
        error = {
            "code": 0,
            "message": "Odoo Server Error",
            "data": data,
        }
        return request.prepare_response(html_escape(json.dumps(error)))

    def _get_response_headers(self, file_type, file_name, file_content):
        headers = [
            (
                "Content-Type",
                request.env["account.report"].get_export_mime_type(file_type),
            ),
            ("Content-Disposition", prepare_content_disposition_header(file_name)),
        ]

        if file_type in ("xml", "txt", "csv", "kvr", "csv") and not isinstance(
            file_content, GeneratorType
        ):
            headers.append(("Content-Length", len(file_content)))

        return headers

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
