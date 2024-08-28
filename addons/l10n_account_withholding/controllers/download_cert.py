# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import zipfile

from odoo import _, http
from odoo.http import content_disposition, request


class AccountWithholdingCertificateDownloadController(http.Controller):

    @http.route('/l10n_account_withholding/download_invoice_withholding_certificate/<models("ir.attachment"):attachments>', type='http', auth='user')
    def download_invoice_attachments(self, attachments):
        """ Similar to what is done in account, but as we need a binary field for manual upload => we need to take the name from somewhere else. """
        attachments.check_access_rights('read')
        attachments.check_access_rule('read')
        assert all(attachment.res_id and attachment.res_model == 'account.move' for attachment in attachments)
        invoices = request.env['account.move'].browse(set(attachments.mapped('res_id')))
        if len(attachments) == 1:
            # We want to keep the same extension, but rename the file.
            filename = invoices._get_invoice_report_filename(extension=attachments.name.split('.')[-1])
            mimetype = attachments.mimetype
            content = attachments.raw
        else:
            if len(invoices) == 1:
                filename = invoices._get_invoice_report_filename(extension='zip')
            else:
                filename = _('invoices_withholding_certs') + '.zip'
            mimetype = 'zip'

            invoice_per_id = invoices.grouped('id')
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zipfile_obj:
                # As one invoice could have multiple files, and we want to differentiate between invoices, we will give
                # unique and clear name to each file.
                for invoice_id, attachments in attachments.grouped('res_id').items():
                    invoice = invoice_per_id[invoice_id]
                    for index, attachment in enumerate(attachments, start=1):
                        zipfile_obj.writestr(f"{invoice.name.replace('/', '_')}_{index}.{attachment.name.split('.')[-1]}", attachment.raw)
            content = buffer.getvalue()

        return request.make_response(content, [
            ('Content-Type', mimetype),
            ('Content-Length', len(content)),
            ('Content-Disposition', content_disposition(filename)),
            ('X-Content-Type-Options', 'nosniff'),
        ])
