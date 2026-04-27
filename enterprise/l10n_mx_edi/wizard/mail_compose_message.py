# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, models


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    def _prepare_mail_values_dynamic(self, res_ids):
        mail_values_all = super()._prepare_mail_values_dynamic(res_ids)
        if self.model == 'account.payment':
            records = self.env[self.model].browse(res_ids).filtered('l10n_mx_edi_cfdi_attachment_id')
            for record in records:
                record_result = mail_values_all.setdefault(record.id, {})
                record_result.setdefault('attachment_ids', []).append(Command.link(record.l10n_mx_edi_cfdi_attachment_id.id))

        return mail_values_all
