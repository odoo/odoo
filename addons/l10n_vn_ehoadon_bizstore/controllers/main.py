# -*- coding: utf-8 -*-
from urllib.parse import quote

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request


class EhoadonPreviewController(http.Controller):
    """Xem trước PDF eHoaDon trực tiếp trên trình duyệt, KHÔNG lưu file vào DB."""

    @http.route('/ehoadon/preview/<int:move_id>', type='http', auth='user')
    def preview_pdf(self, move_id, **kwargs):
        env = request.env
        if not env.user.has_group('l10n_vn_ehoadon_bizstore.group_ehoadon_preview'):
            return request.not_found()
        move = env['account.move'].browse(move_id).exists()
        if not move:
            return request.not_found()
        try:
            move.check_access('read')
        except AccessError:
            return request.not_found()
        try:
            raw, file_name, _mimetype = move._ehoadon_fetch_file_content('pdf')
        except UserError as e:
            message = e.args[0] if e.args else str(e)
            return request.make_response(
                message,
                headers=[('Content-Type', 'text/plain; charset=utf-8')],
                status=400,
            )
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', str(len(raw))),
            ('Content-Disposition', "inline; filename*=UTF-8''%s" % quote(file_name or 'invoice.pdf')),
            ('X-Content-Type-Options', 'nosniff'),
            ('Cache-Control', 'private, no-store'),
        ]
        return request.make_response(raw, headers=headers)
