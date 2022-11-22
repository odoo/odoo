from odoo import models, fields, _


class PosOrder(models.Model):
    _inherit = "pos.order"

    _sequence_field = "customer_sequence"
    _sequence_date_field = "date_order"

    customer_name = fields.Char(related="partner_id.name", store=True)
    customer_sequence = fields.Char("test", compute="_compute_customer_sequence", store=True, index=True)

    def _prepare_invoice_vals(self):
        """
            Override to set the field l10n_sa_pos_origin to True on the invoices generated from a POS order.
            This helps us determine whether an invoice is Simplified or not for the sake of ZATCA e-invoicing
        :return:
        """
        res = {
            **super(PosOrder, self)._prepare_invoice_vals(),
            'l10n_sa_pos_origin': True
        }
        if self.amount_total < 0:
            res['l10n_sa_reversal_reason'] = _("POS Refund")
        return res
