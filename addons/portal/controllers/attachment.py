# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import consteq
from odoo import http, _, SUPERUSER_ID
from odoo.http import request
from odoo.addons.mail.controllers import attachment
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context
from odoo.exceptions import AccessError, MissingError, UserError


def _document_check_access(model_name, document_id, access_token=None):
    """Check if current user is allowed to access the specified record.

    :param str model_name: model of the requested record
    :param int document_id: id of the requested record
    :param str access_token: record token to check if user isn't allowed to read requested record
    :raise MissingError: record not found in database, might have been deleted
    :raise AccessError: current user isn't allowed to read requested document (and no valid token was given)
    """
    document = request.env[model_name].browse([document_id])
    document_sudo = document.with_user(SUPERUSER_ID).exists()
    if not document_sudo:
        raise MissingError(_("This document does not exist."))
    try:
        document.check_access_rights('read')
        document.check_access_rule('read')
    except AccessError:
        if not access_token or not document_sudo.access_token or not consteq(document_sudo.access_token, access_token):
            raise


class AttachmentController(attachment.AttachmentController):

    @http.route("/mail/attachment/upload", methods=["POST"], type="http", auth="public")
    @add_guest_to_context
    def mail_attachment_upload(self, ufile, thread_id, thread_model, is_pending=False, **kwargs):
        try:
            _document_check_access(thread_model, int(thread_id), access_token=kwargs.get('token'))
        except (AccessError, MissingError) as e:
            raise UserError(_("The document does not exist or you do not have the rights to access it."))
        return super().mail_attachment_upload(ufile, thread_id, thread_model, is_pending, **kwargs)
