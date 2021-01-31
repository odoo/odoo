###################################################################################
# 
#    Copyright (C) 2020 Cetmix OÜ
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU LESSER GENERAL PUBLIC LICENSE as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################

import json

import werkzeug

from odoo import http
from odoo.http import request
from odoo.tools.safe_eval import safe_eval, time

from odoo.addons.http_routing.models.ir_http import slugify
from odoo.addons.web.controllers.main import ReportController

# List of content types that will be opened in browser
OPEN_BROWSER_TYPES = ["application/pdf"]


######################
# Report Controllers #
######################
class CxReportController(ReportController):
    @http.route(
        [
            "/report/<converter>/<reportname>",
            "/report/<converter>/<reportname>/<docids>",
        ],
        type="http",
        auth="user",
        website=True,
    )
    def report_routes(self, reportname, docids=None, converter=None, **data):
        report = request.env["ir.actions.report"]._get_report_from_name(reportname)
        context = dict(request.env.context)

        if docids:
            docids = [int(i) for i in docids.split(",")]
        if data.get("options"):
            data.update(json.loads(data.pop("options")))
        if data.get("context"):
            data["context"] = json.loads(data["context"])
            if data["context"].get("lang"):
                del data["context"]["lang"]
            context.update(data["context"])
        if converter == "html":
            html = report.with_context(context)._render_qweb_html(docids, data=data)[0]
            return request.make_response(html)
        elif converter == "pdf":

            # Get filename for report
            filepart = "report"

            if docids:
                if len(docids) > 1:
                    filepart = "{} (x{})".format(
                        request.env["ir.model"]
                        .sudo()
                        .search([("model", "=", report.model)])
                        .name,
                        str(len(docids)),
                    )
                elif len(docids) == 1:
                    obj = request.env[report.model].browse(docids)
                    if report.print_report_name:
                        filepart = safe_eval(
                            report.print_report_name, {"object": obj, "time": time}
                        )

            pdf = report.with_context(context)._render_qweb_pdf(docids, data=data)[0]
            pdfhttpheaders = [
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf)),
                ("Content-Disposition", 'filename="%s.pdf"' % slugify(filepart)),
            ]
            return request.make_response(pdf, headers=pdfhttpheaders)
        elif converter == "text":
            text = report.with_context(context)._render_qweb_text(docids, data=data)[0]
            texthttpheaders = [
                ("Content-Type", "text/plain"),
                ("Content-Length", len(text)),
            ]
            return request.make_response(text, headers=texthttpheaders)
        else:
            raise werkzeug.exceptions.HTTPException(
                description="Converter %s not implemented." % converter
            )
