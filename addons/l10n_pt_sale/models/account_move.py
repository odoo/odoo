from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        # A final invoice deducts the down payments invoiced before: those invoices have to be issued.
        final_invoices = self.filtered(lambda m: m._l10n_pt_country_ok() and m.move_type == 'out_invoice')
        deductions = final_invoices.invoice_line_ids.filtered(lambda line: line.is_downpayment and line.quantity < 0)
        (deductions._get_downpayment_lines().move_id - self)._l10n_pt_check_issued(self.env._("A final invoice"))
        return super()._post(soft)

    def _l10n_pt_is_invoice_receipt(self):
        return (
            super()._l10n_pt_is_invoice_receipt()
            or (
                self._l10n_pt_country_ok()
                and self.move_type == 'out_invoice'
                and any(tx.state == 'done' for tx in self.line_ids.sale_line_ids.order_id.transaction_ids)
            )
        )


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _l10n_pt_get_non_positive_lines(self):
        # EXTENDS l10n_pt_certification: a final invoice deducts the down payments invoiced before as negative lines.
        return super()._l10n_pt_get_non_positive_lines().filtered(lambda line: not line.is_downpayment)
