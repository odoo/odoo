# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

import base64
import json
import logging

from werkzeug.urls import url_decode

from odoo import http
from odoo.http import content_disposition, request, route, serialize_exception
from odoo.tools import html_escape
from odoo.tools.safe_eval import safe_eval, time

from odoo.addons.web.controllers import report

_logger = logging.getLogger(__name__)


class ReportController(report.ReportController):
    @route()
    def report_routes(self, reportname, docids=None, converter=None, **data):
        if converter == "excel":
            report = request.env["ir.actions.report"]._get_report_from_name(reportname)
            context = dict(request.env.context)
            if docids:
                docids = [int(i) for i in docids.split(",")]
            if data.get("options"):
                data.update(json.loads(data.pop("options")))
            if data.get("context"):
                # Ignore 'lang' here, because the context in data is the one
                # from the webclient *but* if the user explicitely wants to
                # change the lang, this mechanism overwrites it.
                data["context"] = json.loads(data["context"])
                if data["context"].get("lang"):
                    del data["context"]["lang"]
                context.update(data["context"])

            excel, report_name = report.with_context(**context)._render_excel(
                docids, data=data
            )
            excel = base64.decodebytes(excel)
            if docids:
                records = request.env[report.model].browse(docids)
                if report.print_report_name and not len(records) > 1:
                    # this is a bad idea, this should only be .xlsx
                    extension = report_name.split(".")[-1:].pop()
                    report_name = safe_eval(
                        report.print_report_name, {"object": records, "time": time}
                    )
                    report_name = f"{report_name}.{extension}"
            excelhttpheaders = [
                (
                    "Content-Type",
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet",
                ),
                ("Content-Length", len(excel)),
                ("Content-Disposition", content_disposition(report_name)),
            ]
            return request.make_response(excel, headers=excelhttpheaders)
        return super().report_routes(reportname, docids, converter, **data)

    @http.route()
    def report_download(self, data, context=None):
        requestcontent = json.loads(data)
        url, report_type = requestcontent[0], requestcontent[1]
        if report_type != "excel":
            return super().report_download(data, context)
        reportname = "???"
        try:
            pattern = "/report/excel/"
            reportname = url.split(pattern)[1].split("?")[0]
            docids = None
            if "/" in reportname:
                reportname, docids = reportname.split("/")
            if docids:
                return self.report_routes(
                    reportname, docids=docids, converter="excel", context=context
                )
            data = dict(url_decode(url.split("?")[1]).items())
            if "context" in data:
                context, data_context = json.loads(context or "{}"), json.loads(
                    data.pop("context")
                )
                context = json.dumps({**context, **data_context})
            return self.report_routes(
                reportname, converter="excel", context=context, **data
            )
        except Exception as e:
            _logger.exception("Error while generating report %s", reportname)
            se = serialize_exception(e)
            error = {"code": 200, "message": "Odoo Server Error", "data": se}
            return request.make_response(html_escape(json.dumps(error)))
