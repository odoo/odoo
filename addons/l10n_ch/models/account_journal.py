from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    invoice_reference_model = fields.Selection(
        selection_add=[("ch", "Switzerland (12 34560 00103 88500 1000 19188)")],
        ondelete={"ch": lambda recs: recs.write({"invoice_reference_model": "odoo"})},
    )

    def _process_reference_for_sale_order(self, order_reference):
        """
        Returns the order reference to be used for the payment, respecting the QRR standard.
        """
        self.check_singleton()
        if self.invoice_reference_model == "ch":
            # converting the sale order name into a unique number. Letters are converted to their base10 value
            invoice_ref = "".join(
                [a if a.isdigit() else str(ord(a)) for a in order_reference]
            )
            return self.env["account.move"]._get_qrr_number(invoice_ref)
        return super()._process_reference_for_sale_order(order_reference)
