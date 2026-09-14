import logging
from typing import Any
from urllib.parse import parse_qs, urlsplit

from odoo import http
from odoo.http import (
    BadRequest,
    InternalServerError,
    Response,
    prepare_content_disposition_header,
    request,
)
from odoo.libs.json import dumps as json_dumps
from odoo.libs.json import loads as json_loads
from odoo.tools.misc import html_escape
from odoo.tools.safe_eval import safe_eval, time

from ..tools import debug_log as dbg

_logger = logging.getLogger(__name__)

_MAX_BARCODE_DIM = 10_000

_MAX_BARCODE_VALUE_LEN = 4096


def _clamp_barcode_dimension(raw: Any, default: int) -> int:
    try:
        value = int(raw)
    except ValueError, TypeError:
        return default
    if value < 1:
        return default
    return min(value, _MAX_BARCODE_DIM)


class ReportController(http.Controller):
    @http.route(
        [
            "/report/<converter>/<reportname>",
            "/report/<converter>/<reportname>/<docids>",
        ],
        type="http",
        auth="user",
        website=True,
        readonly=True,
    )
    def report_routes(
        self,
        reportname: str,
        docids: str | None = None,
        converter: str | None = None,
        **data,
    ) -> Response:
        dbg.lifecycle.debug(
            "[report:%s] routes: %s converter=%s docids=%r data=%s",
            reportname,
            dbg.req(),
            converter,
            docids,
            dbg.keys(data),
        )
        report = request.env["ir.actions.report"]
        context = dict(request.env.context)

        if docids:
            docids = [int(i) for i in docids.split(",") if i.isdigit()]
        if data.get("options"):
            data.update(json_loads(data.pop("options")))
            dbg.logic.debug(
                "[report:%s] routes: options merged -> data=%s",
                reportname,
                dbg.keys(data),
            )
        if data.get("context"):
            data["context"] = json_loads(data["context"])
            context.update(data["context"])
            dbg.logic.debug(
                "[report:%s] routes: context extended with %s",
                reportname,
                dbg.keys(data["context"]),
            )
        dbg.pipeline.debug(
            "[report:%s] routes: render %s for %s docs",
            reportname,
            converter,
            dbg.count(docids or ()),
        )
        if converter == "html":
            with dbg.timer(request.env, "[report:%s] render html", reportname):
                html = report.with_context(context)._render_qweb_html(
                    reportname, docids, data=data
                )[0]
            dbg.performance.debug("[report:%s] html: %d chars", reportname, len(html))
            return request.prepare_response(html)
        elif converter == "pdf":
            with dbg.timer(request.env, "[report:%s] render pdf", reportname):
                pdf = report.with_context(context)._render_qweb_pdf(
                    reportname, docids, data=data
                )[0]
            dbg.performance.debug("[report:%s] pdf: %d bytes", reportname, len(pdf))
            pdfhttpheaders = [
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf)),
            ]
            return request.prepare_response(pdf, headers=pdfhttpheaders)
        elif converter == "text":
            with dbg.timer(request.env, "[report:%s] render text", reportname):
                text = report.with_context(context)._render_qweb_text(
                    reportname, docids, data=data
                )[0]
            dbg.performance.debug("[report:%s] text: %d chars", reportname, len(text))
            texthttpheaders = [
                ("Content-Type", "text/plain"),
                ("Content-Length", len(text)),
            ]
            return request.prepare_response(text, headers=texthttpheaders)
        else:
            dbg.logic.debug(
                "[report:%s] routes: converter %r unsupported", reportname, converter
            )
            raise BadRequest(description=f"Converter {converter!r} not supported.")

    @http.route(
        [
            "/report/barcode",
            "/report/barcode/<barcode_type>/<path:value>",
        ],
        type="http",
        auth="public",
        readonly=True,
    )
    def report_barcode(self, barcode_type: str, value: str, **kwargs) -> Response:
        dbg.lifecycle.debug(
            "[barcode:%s] %s value_len=%s kwargs=%s",
            barcode_type,
            dbg.req(),
            len(value) if value is not None else None,
            dbg.keys(kwargs),
        )
        if value is not None and len(value) > _MAX_BARCODE_VALUE_LEN:
            dbg.logic.debug("[barcode:%s] value too long, refused", barcode_type)
            raise BadRequest("Barcode value is too long.")
        if "width" in kwargs:
            kwargs["width"] = _clamp_barcode_dimension(kwargs["width"], 600)
        if "height" in kwargs:
            kwargs["height"] = _clamp_barcode_dimension(kwargs["height"], 100)
        try:
            with dbg.timer(request.env, "[barcode:%s] prepare", barcode_type):
                barcode = request.env["ir.actions.report"].prepare_barcode(
                    barcode_type, value, **kwargs
                )
        except (ValueError, AttributeError, KeyError) as exc:
            dbg.logic.debug(
                "[barcode:%s] cannot convert (%s)", barcode_type, type(exc).__name__
            )
            raise BadRequest("Cannot convert into barcode.") from None
        dbg.performance.debug("[barcode:%s] %d bytes png", barcode_type, len(barcode))

        return request.prepare_response(
            barcode,
            headers=[
                ("Content-Type", "image/png"),
                (
                    "Cache-Control",
                    f"public, max-age={http.STATIC_CACHE_LONG}, immutable",
                ),
            ],
        )

    @http.route(["/report/download"], type="http", auth="user")
    def report_download(
        self, data: str, context: str | None = None, **_kwargs
    ) -> Response:
        requestcontent = json_loads(data)
        url, type_ = requestcontent[0], requestcontent[1]
        reportname = "???"
        dbg.lifecycle.debug(
            "[report_download] %s type=%s url=%r has_context=%s",
            dbg.req(),
            type_,
            url,
            context is not None,
        )
        try:
            if type_ in ["qweb-pdf", "qweb-text"]:
                converter = "pdf" if type_ == "qweb-pdf" else "text"
                extension = "pdf" if type_ == "qweb-pdf" else "txt"

                pattern = "/report/pdf/" if type_ == "qweb-pdf" else "/report/text/"
                _, _, after_pattern = url.partition(pattern)
                if not after_pattern:
                    dbg.logic.debug("[report_download] url lacks %r, refused", pattern)
                    raise BadRequest(
                        description=f"URL does not match expected pattern {pattern!r}."
                    )
                reportname = after_pattern.split("?")[0]

                docids = None
                if "/" in reportname:
                    reportname, docids = reportname.split("/", 1)
                dbg.pipeline.debug(
                    "[report:%s] download: %s docids=%r via %s",
                    reportname,
                    converter,
                    docids,
                    "docids" if docids else "query string",
                )

                if docids:
                    response = self.report_routes(
                        reportname,
                        docids=docids,
                        converter=converter,
                        context=context,
                    )
                else:
                    data = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
                    if "context" in data:
                        context, data_context = (
                            json_loads(context or "{}"),
                            json_loads(data.pop("context")),
                        )
                        context = json_dumps({**context, **data_context})
                    response = self.report_routes(
                        reportname, converter=converter, context=context, **data
                    )

                report = request.env["ir.actions.report"]._get_report_from_name(
                    reportname
                )
                filename = f"{report.name}.{extension}"

                if docids:
                    ids = [int(x) for x in docids.split(",") if x.isdigit()]
                    obj = request.env[report.model].browse(ids)
                    if report.print_report_name and len(obj) == 1:
                        report_name = safe_eval(
                            report.print_report_name,
                            {"object": obj, "time": time},
                        )
                        filename = f"{report_name}.{extension}"
                        dbg.logic.debug(
                            "[report:%s] download: print_report_name -> %r",
                            reportname,
                            filename,
                        )
                response.headers.add(
                    "Content-Disposition", prepare_content_disposition_header(filename)
                )
                dbg.pipeline.debug(
                    "[report:%s] download: attachment %r", reportname, filename
                )
                return response
            else:
                dbg.logic.debug("[report_download] type %r unsupported", type_)
                raise BadRequest(description=f"Report type {type_!r} not supported.")
        except Exception as e:
            dbg.logic.debug(
                "[report:%s] download: failed (%s) -> 500 json envelope",
                reportname,
                type(e).__name__,
            )
            _logger.warning(
                "Error while generating report %s", reportname, exc_info=True
            )
            se = http.serialize_exception(e)
            error = {"code": 0, "message": "Odoo Server Error", "data": se}
            res = request.prepare_response(html_escape(json_dumps(error)))
            raise InternalServerError(response=res) from e
