from odoo import fields, models

class EwayBillCancel(models.TransientModel):
    _name = "eway.bill.cancel"

    cancel_reason = fields.Selection(selection=[
        ("duplicate", "Duplicate"),
        ("data_entry_mistake", "Data Entry Mistake"),
        ("order_cancelled", "Order Cancelled"),
        ("others", "Others"),
        ], string="Cancel reason", copy=False)
    cancel_remarks = fields.Char("Cancel remarks", copy=False)

    def cancel_eway(self):
        record = self.env['account.move'].browse(self._context.get('active_ids'))
        record.l10n_in_edi_cancel_reason = self.cancel_reason
        record.l10n_in_edi_cancel_remarks = self.cancel_remarks
        record.button_cancel_posted_eway()
