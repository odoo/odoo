from odoo.exceptions import ValidationError
from odoo import fields, models, _

class EwayInvoiceCancel(models.TransientModel):
    _name = "einvoice.cancel"

    cancel_reason = fields.Selection(selection=[
        ("duplicate", "Duplicate"),
        ("data_entry_mistake", "Data Entry Mistake"),
        ("order_cancelled", "Order Cancelled"),
        ("others", "Others"),
        ], string="Cancel reason", copy=False)
    cancel_remarks = fields.Char("Cancel remarks", copy=False)

    def cancel_einvoice(self):
        record = self.env['account.move'].browse(self._context.get('active_ids'))
        record.l10n_in_edi_cancel_reason = self.cancel_reason
        record.l10n_in_edi_cancel_remarks = self.cancel_remarks
        if all(doc.edi_format_id.code == "in_ewaybill_1_03" for doc in record.edi_document_ids):
            raise ValidationError(_("You don't have a E-Invoice to cancel."))
        if any(doc.edi_format_id.code == "in_ewaybill_1_03" and doc.state in ['sent', 'to_cancel'] for doc in record.edi_document_ids):
            raise ValidationError(_("You have a existing E-way Bill linked to the E-Invoice. So cancel the E-way Bill first to cancel the E-invoice."))
        record.button_cancel_posted_moves()
       