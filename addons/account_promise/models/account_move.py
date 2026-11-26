from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def button_cancel(self):
        result = super().button_cancel()

        promises = self.env["account.payment.promise"].search(
            [
                ("invoice_ids", "in", self.ids),
                ("state", "=", "open"),
            ],
        )

        promises.write(
            {
                "state": "cancelled",
                "note": "Promise cancelled because invoice is cancelled",
            },
        )

        return result

    def button_draft(self):
        result = super().button_draft()

        promises = self.env["account.payment.promise"].search(
            [
                ("invoice_ids", "in", self.ids),
                ("state", "=", "open"),
            ],
        )

        promises.write(
            {
                "state": "cancelled",
                "note": "Promise cancelled because invoice got reset to draft",
            },
        )

        return result
