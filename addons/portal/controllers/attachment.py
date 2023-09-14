# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import consteq
from odoo import http, SUPERUSER_ID
from odoo.http import request
from odoo.addons.mail.controllers import attachment
from odoo.exceptions import AccessError


def _document_check_access(model_name, document_id, access_token=None):
    """Check if current user is allowed to access the specified record.

    :param str model_name: model of the requested record
    :param int document_id: id of the requested record
    :param str access_token: record token to check if user isn't allowed to read requested record
    """
    document = request.env[model_name].browse([document_id])
    document_sudo = document.with_user(SUPERUSER_ID).exists()
    if not document_sudo:
        return False
    try:
        document.check_access_rights('read')
        document.check_access_rule('read')
    except AccessError:
        if not access_token or not document_sudo.access_token or not consteq(document_sudo.access_token, access_token):
            return False
    return True


class AttachmentController(attachment.AttachmentController):

    @http.route("/mail/attachment/upload", methods=["POST"], type="http", auth="public")
    def mail_attachment_upload(self, ufile, thread_id, thread_model, is_pending=False, **kwargs):
        if _document_check_access(thread_model, int(thread_id), access_token=kwargs.get('token')):
            kwargs['force_sudo'] = True
        return super().mail_attachment_upload(ufile, thread_id, thread_model, is_pending, **kwargs)
