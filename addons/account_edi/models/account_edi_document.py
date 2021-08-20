# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountEdiDocument(models.Model):
    _inherit = 'account.edi.document'

    def _cancel_records(self, records):
        # The user requested a cancellation of the EDI and it has been approved. Then, the invoice
        # can be safely cancelled.
        if 'invoice' in records:
            invoices_to_cancel = records['invoice'].filtered(lambda i: i.state == 'posted')
            invoices_to_cancel.button_draft()
            invoices_to_cancel.button_cancel()
        super()._cancel_records(records)
