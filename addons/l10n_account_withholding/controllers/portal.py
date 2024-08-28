# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, _, http
from odoo.addons.account.controllers.portal import PortalAccount
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request


class PortalAccountWithholding(PortalAccount):

    @http.route(['/my/invoices/upload_withholding_certificate'], type='http', auth="public", website=True)
    def portal_my_invoice_upload_withholding_certificate(self, name, file, thread_model, thread_id, access_token=None):
        try:
            invoice = self._document_check_access(thread_model, int(thread_id), access_token=access_token)
        except (AccessError, MissingError):
            raise UserError(_("The document does not exist or you do not have the rights to access it."))

        IrAttachment = request.env['ir.attachment']

        # Avoid using sudo when not necessary: internal users can create attachments,
        # as opposed to public and portal users.
        if not request.env.user._is_internal():
            IrAttachment = IrAttachment.sudo()

        attachment_data = file.read()
        attachment_name = name.replace('\x3c', '')

        # As it could be possible that multiple certificates are linked to a single invoice, we will store them.
        # We still distinguish between the first document added and the next ones, as it should be uncommon.
        if not invoice.l10n_account_withholding_certificate_ids:
            message = _('A new withholding tax certificate has been uploaded')
        else:
            message = _('An additional withholding tax certificate has been uploaded')

        invoice.l10n_account_withholding_certificate_ids = [Command.create({
            'name': attachment_name,
            'raw': attachment_data,
            'type': 'binary',
            'res_model': thread_model,
            'res_id': int(thread_id),
            'access_token': IrAttachment._generate_access_token(),
        })]

        # Lastly, we trigger a message post sent by the user uploading the certificate.
        # The aim is to keep track of all uploads in the chatter, and also display it on the portal to keep a trace that
        # it has been sent.
        invoice.with_context(no_new_invoice=True).message_post(
            body=message,
            attachments=[(attachment_name, attachment_data)],  # Copy of the one in the field, so that we never lose the original file.
            author_id=request.env.user.partner_id.id,
            # So that the portal user see their upload message
            message_type='comment',
            subtype_id=request.env.ref('mail.mt_comment').id,
        )
        return request.make_response('ok')
