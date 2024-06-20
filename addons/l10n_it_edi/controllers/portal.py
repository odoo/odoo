from odoo.http import Controller, request, route


class FatturaElettronicaController(Controller):
    @route(
        [
            "/fatturapa/preview/<attachment_id>",
        ],
        type="http",
        auth="user",
        website=True,
    )
    def fatturapa_preview(self, attachment_id, **data):
        attach = request.env["ir.attachment"].browse(int(attachment_id))
        html = attach.get_fattura_elettronica_preview()
        if isinstance(html, bytes):
            html = html.decode()
        pdf = request.env["ir.actions.report"]._run_wkhtmltopdf([html])

        pdfhttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(pdf)),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)
