# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import zipfile
from collections import defaultdict

from odoo import http, _
from odoo.exceptions import UserError
from odoo.http import request, content_disposition


def _get_headers(filename, filetype, content):
    return [
        ('Content-Type', filetype),
        ('Content-Length', len(content)),
        ('Content-Disposition', content_disposition(filename)),
        ('X-Content-Type-Options', 'nosniff'),
    ]


def _generate_error_txt_file(missing_documents: list[str]):
    content = request.env._("Error: Couldn't Generate Documents for the Following\n")
    content += "\n".join(missing_documents)
    return {
        'filename': "error.txt",
        'filetype': 'text/plain',
        'content': content,
    }


def rename_duplicates(docs):
    seen = {}
    for doc in docs:
        name = doc["filename"]
        if name not in seen:
            seen[name] = 0
        else:
            seen[name] += 1
            base, *ext = name.rsplit('.', 1)
            name = f"{base} ({seen[name]})" + f".{ext[0]}" if ext else ""
            doc["filename"] = name
            seen[name] = 0

    return docs


def _build_zip_from_data(docs_data):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zipfile_obj:
        for doc_data in docs_data:
            zipfile_obj.writestr(doc_data['filename'], doc_data['content'])
    return buffer.getvalue()


class AccountDocumentDownloadController(http.Controller):

    @http.route('/account/download_invoice_attachments/<models("ir.attachment"):attachments>', type='http', auth='user')
    def download_invoice_attachments(self, attachments):
        attachments.check_access('read')
        assert all(attachment.res_id and attachment.res_model == 'account.move' for attachment in attachments)
        if len(attachments) == 1:
            headers = _get_headers(attachments.name, attachments.mimetype, attachments.raw)
            return request.make_response(attachments.raw, headers)
        else:
            inv_ids = attachments.mapped('res_id')
            if len(set(inv_ids)) == 1:
                invoice = request.env['account.move'].browse(inv_ids[0])
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
                if (errors := doc_data.get('errors')) and len(invoices) == 1:
                    raise UserError(_("Error while creating XML:\n- %s", '\n- '.join(errors)))
                docs_data.append(doc_data)
        if len(docs_data) == 1:
            doc_data = docs_data[0]
            headers = _get_headers(doc_data['filename'], doc_data['filetype'], doc_data['content'])
            return request.make_response(doc_data['content'], headers)
        if len(docs_data) > 1:
            zip_content = _build_zip_from_data(docs_data)
            headers = _get_headers(_('invoices') + '.zip', 'zip', zip_content)
            return request.make_response(zip_content, headers)
        raise UserError(_("There are no available documents to export."))

    @http.route('/account/download_move_attachments/<models("account.move"):moves>', type='http', auth='user')
    def _get_move_attachments(self, moves):
        moves_docs = defaultdict(list)
        for move in moves:
            moves_docs[move.id] += move._get_invoice_legal_documents_all() or []
            if move.move_type in ('in_invoice', 'in_refund', 'in_receipt') and (attachment := move.message_main_attachment_id):
                moves_docs[move.id].append({
                    'filename': attachment.name,
                    'filetype': attachment.mimetype,
                    'content': attachment.raw,
                })

        if docs_data := [doc for docs in moves_docs.values() for doc in docs]:

            if missing_moves := [move.name for move in moves if not moves_docs[move.id]]:
                docs_data.append(_generate_error_txt_file(missing_moves))

            docs_data = rename_duplicates(docs_data)
            zip_content = _build_zip_from_data(docs_data)
            headers = _get_headers(request.env._("Moves") + '.zip', 'zip', zip_content)
            return request.make_response(zip_content, headers)
        raise UserError(request.env._("There are no available documents to export. Please ensure the selected invoices have been sent or contain PDF/XML files."))
