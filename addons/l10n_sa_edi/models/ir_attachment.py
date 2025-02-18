from odoo import models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def register_as_main_attachment(self, force=False):
        if self.res_model == 'account.move':
            move = self.env[self.res_model].browse(self.res_id)
            if move.is_invoice() and move.country_code == 'SA':
                if not move.l10n_sa_confirmation_datetime or not move.edi_document_ids:
                    return
                invoice_name = self.env['account.edi.xml.ubl_21.zatca']._export_invoice_filename(move, 'pdf')
                force = invoice_name == self.name
                if not force:
                    return
        return super().register_as_main_attachment(force)
