from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        # A final invoice deducts the down payments invoiced before: those invoices have to be issued.
        final_invoices = self.filtered(lambda m: m._l10n_pt_country_ok() and m.move_type == 'out_invoice')
        deductions = final_invoices.invoice_line_ids.filtered(lambda l: l.is_downpayment and l.quantity < 0)
        (deductions._get_downpayment_lines().move_id - self)._l10n_pt_check_issued(self.env._("A final invoice"))
        return super()._post(soft)

    def _l10n_pt_is_invoice_receipt(self):
        return (
            super()._l10n_pt_is_invoice_receipt()
            or (
                self._l10n_pt_country_ok()
                and self.move_type == 'out_invoice'
                and self.line_ids.sale_line_ids.order_id.transaction_ids.filtered(lambda tx: tx.state == 'done')
            )
        )
