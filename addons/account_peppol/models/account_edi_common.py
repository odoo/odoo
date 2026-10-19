from odoo import models


class AccountEdiCommon(models.AbstractModel):
    _inherit = 'account.edi.common'

    def _add_logs_import_invoice_ubl_cii(self, invoice, invoice_logs=None):
        # EXTENDS 'account_edi_ubl_cii'
        logs = super()._add_logs_import_invoice_ubl_cii(invoice, invoice_logs=invoice_logs)
        if uuid := invoice.peppol_message_uuid:
            logs = [self.env._("Peppol document UUID: %s", uuid)] + logs
        return logs

    def _log_import_invoice_ubl_cii(self, invoice, title_logs=None, invoice_logs=None, attachments=None):
        # EXTENDS 'account_edi_ubl_cii'
        if invoice.peppol_message_uuid:
            title_logs = self.env._("Peppol invoice received")
        super()._log_import_invoice_ubl_cii(invoice, title_logs=title_logs, invoice_logs=invoice_logs, attachments=attachments)
