# -*- coding: utf-8 -*-

import io
from odoo.addons.web.controllers import main as report
import xlrd

import odoo
from odoo import http
from odoo.tools.safe_eval import safe_eval,time
from odoo.http import content_disposition, route, request
import werkzeug
import json
from werkzeug import urls
from odoo.addons.http_routing.models.ir_http import slugify

# List of content types that will be opened in browser
OPEN_BROWSER_TYPES = ["application/pdf"]


class ReportController(report.ReportController):

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
        if converter == 'fastreport':
            report_jas = request.env[
                'ir.actions.report']._get_report_from_name(reportname)
            context = dict(request.env.context)
            if docids:
                docids = [int(i) for i in docids.split(',')]
            if data.get('options'):
                data.update(json.loads(data.pop('options')))
            if data.get('context'):
                # Ignore 'lang' here, because the context in data is the one
                # from the webclient *but* if the user explicitely wants to
                # change the lang, this mechanism overwrites it.
                data['context'] = json.loads(data['context'])
                if data['context'].get('lang'):
                    del data['context']['lang']
                context.update(data['context'])

           # Get the report and output type
            jaspers, output_type = report_jas.with_context(
                context).render_fastreport(docids, data=data)
            jasper = io.BytesIO(jaspers)
            report_name = str(report_jas.name) + '.' + output_type
            content_dict = {
                'pdf': 'application/pdf',
                'html': 'application/html',
                'csv': 'text/csv',
                'xls': 'application/xls',
                'rtf': 'application/octet-stream',
                'odt': 'application/vnd.oasis.opendocument.text',
                'ods': 'application/vnd.oasis.opendocument.spreadsheet',
                'txt': 'text/plain',
            }
            filename = odoo.tools.ustr(report_name)
            escaped = urls.url_quote(filename, safe='')

            content_disp = "inline; filename*=UTF-8''%s" % escaped
            pdfhttpheaders = [
                ('Content-Type', content_dict.get(output_type)),
                ('Content-Length', len(jaspers)),
                ('Content-Disposition',content_disp)
            ]
            response = request.make_response(jasper, headers=pdfhttpheaders)
            #token = data.get('token')
            #response.set_cookie('fileToken', token)
            return response

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
            # print(request.make_response(pdf, headers=pdfhttpheaders))
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
        return super(ReportController, self).report_routes(
            reportname, docids, converter, **data)

    @http.route(
        ["/report/get_report_structure"],
        type="http",
        auth="user",
        methods=['GET'],
        website=True,
    )
    def get_report_structure(self):
        report_model = request.env['ir.actions.report']
        struct_result = report_model.read_report_structure()
        httpheaders = [("Content-Type", "application/json")]
        return request.make_response(json.dumps(struct_result,ensure_ascii=False), headers=httpheaders)

    @http.route(
        ["/report/get_report_data"],
        type="http",
        auth="user",
        methods=['GET'],
        website=True,
    )
    def get_report_data(self,report_id,file_id,limit=None):
        report_model = request.env['ir.actions.report']
        limit = int(limit) if limit else 10
        report_data_result = report_model.transfer_report_data(report_id,file_id,limit)
        httpheaders = [
                ("Content-Type", "application/json")]
        return request.make_response(json.dumps(report_data_result,ensure_ascii=False), headers=httpheaders)

    @http.route(
        ["/report/save_report_template"],
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
    )
    def save_report_template(self,report_id,file_id,file_data ):
        report_model = request.env['ir.actions.report']
        temp_data_result = report_model.process_report_file(report_id,file_id,file_data)

        httpheaders = [
                ("Content-Type", "application/json")]
        return request.make_response(json.dumps(temp_data_result,ensure_ascii=False), headers=httpheaders)

