# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import zipfile
from odoo import _, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.http.stream import content_disposition
from odoo.tools import OrderedSet
from odoo.tools.mimetypes import get_extension


def _get_headers(filename, filetype, content):
    return [
        ('Content-Type', filetype),
        ('Content-Length', len(content)),
        ('Content-Disposition', content_disposition(filename)),
        ('X-Content-Type-Options', 'nosniff'),
    ]


def _build_zip_from_data(docs_data):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zipfile_obj:
        for doc_data in docs_data:
            zipfile_obj.writestr(doc_data['filename'], bytes(doc_data['content']))
    return buffer.getvalue()


class AccountDocumentDownloadController(http.Controller):

    @http.route('/account/download_invoice_attachments/<models("ir.attachment"):attachments>', type='http', auth='user')
    def download_invoice_attachments(self, attachments):
        attachments.check_access('read')
        assert all(attachment.res_id and attachment.res_model == 'account.move' for attachment in attachments)
        if len(attachments) == 1:
            content = attachments.raw.content
            headers = _get_headers(attachments.name, attachments.mimetype, content)
            return request.make_response(content, headers)
        else:
            inv_ids = OrderedSet(a.res_id for a in attachments if a.res_id)
            if len(inv_ids) == 1:
                invoice = request.env['account.move'].browse(inv_ids)
                filename = invoice._get_invoice_report_filename(extension='zip')
            else:
                filename = _('invoices') + '.zip'
            content = attachments._build_zip_from_attachments()
            headers = _get_headers(filename, 'zip', content)
            return request.make_response(content, headers)

    @http.route('/account/download_invoice_documents/<models("account.move"):invoices>/<string:filetype>', type='http', auth='user')
    def download_invoice_documents_filetype(self, invoices, filetype, allow_fallback=True):
        invoices.check_access('read')
        invoices.line_ids.check_access('read')
        docs_data = []
        for invoice in invoices:
            if filetype == 'all' and (doc_data := invoice._get_invoice_legal_documents_all(allow_fallback=allow_fallback)):
                docs_data += doc_data
            elif doc_data := invoice._get_invoice_legal_documents(filetype, allow_fallback=allow_fallback):
                if len(invoices) == 1 and (errors := [error for data in docs_data for error in data.get('errors', [])]):
                    raise UserError(_("Error while creating XML:\n- %s", '\n- '.join(errors)))
                docs_data.extend(doc_data)
        if len(docs_data) == 1:
            doc_data = docs_data[0]
            content = bytes(doc_data['content'])
            headers = _get_headers(doc_data['filename'], doc_data['filetype'], content)
            return request.make_response(content, headers)
        if len(docs_data) > 1:
            zip_content = _build_zip_from_data(docs_data)
            headers = _get_headers(_('invoices') + '.zip', 'zip', zip_content)
            return request.make_response(zip_content, headers)
        return None

    @http.route('/account/download_move_attachments/<models("account.move"):moves>', type='http', auth='user')
    def download_move_attachments(self, moves):

        def rename_duplicates(docs):
            seen = {}
            for doc in docs:
                name = doc["filename"]
                if name not in seen:
                    seen[name] = 0
                else:
                    seen[name] += 1
                    base, *ext = name.rsplit('.', 1)
                    new_name = f"{base} ({seen[name]})" + (f".{ext[0]}" if ext else "")
                    doc["filename"] = new_name
                    seen[new_name] = 0
            return docs

        def get_zip_name(moves):
            move_types = set(moves.mapped('move_type'))
            if move_types <= {'in_invoice', 'in_refund', 'in_receipt'}:
                return request.env._("VendorBills")
            if move_types <= {'out_invoice', 'out_refund', 'out_receipt'}:
                return request.env._("CustomerInvoices")
            return request.env._("Documents")

        docs_data = []
        for move in moves:
            move_prefix = move.name.replace('/', '_') if move.name else None
            for doc in move._get_move_zip_export_docs():
                if move_prefix:
                    ext = get_extension(doc["filename"])
                    doc["filename"] = f"{move_prefix}{ext}" if ext else move_prefix
                docs_data.append(doc)

        if docs_data:
            docs_data = rename_duplicates(docs_data)
            zip_content = _build_zip_from_data(docs_data)
            headers = _get_headers(get_zip_name(moves) + '.zip', 'zip', zip_content)
            return request.make_response(zip_content, headers)
        return None
