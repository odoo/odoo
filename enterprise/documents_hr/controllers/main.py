# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import Forbidden

from odoo import http, tools


class DocumentsHrController(http.Controller):

    @http.route(
        "/documents_hr/my_files/<int:employee_id>/<token>",
        type="http", auth="public")
    def my_files(self, employee_id, token):
        """Allow the user to download its file if its user is archived.

        The user will be able to download all files for which he's the partner, under
        the HR companies folders.
        """
        employee = self._check_token(employee_id, token)
        if not employee.work_contact_id:
            raise Forbidden()

        documents = http.request.env["documents.document"].sudo().search([
            ("partner_id", "=", employee.work_contact_id.id),
            ("id", "child_of", employee.company_id.documents_hr_folder.id),
        ])

        return http.request.render("documents_hr.documents_hr_portal_view", {
            "documents": documents,
            "base_url_download": f"/documents_hr/my_files/{employee_id}/{token}",
        })

    @http.route(
        "/documents_hr/my_files/<int:employee_id>/<token>/<int:document_id>",
        type="http", auth="public")
    def my_files_download(self, employee_id, token, document_id):
        employee = self._check_token(employee_id, token)

        document = http.request.env["documents.document"].browse(document_id).sudo().exists()
        if (
            not document
            or not document.parent_path.startswith(employee.company_id.documents_hr_folder.parent_path)
            or document.partner_id != employee.work_contact_id
        ):
            raise Forbidden()

        return http.request.env['ir.binary']._get_stream_from(document).get_response(as_attachment=True)

    @classmethod
    def _check_token(cls, employee_id, token):
        employee = http.request.env['hr.employee'].browse(employee_id).exists().sudo()
        if not employee or not tools.consteq(token, employee._get_employee_documents_token()):
            raise Forbidden()
        return employee
