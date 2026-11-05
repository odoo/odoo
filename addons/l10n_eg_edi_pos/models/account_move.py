from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _is_l10n_eg_edi_applicable(self, mode):
        # EXTENDS 'l10n_eg_edi_eta'
        self.ensure_one()
        # Moves linked to pos.orders are reported to ETA through the pos.order.
        return not self.pos_order_count and super()._is_l10n_eg_edi_applicable(mode)

    def action_post_sign_invoices(self):
        # EXTENDS 'l10n_eg_edi_eta'
        invoices = self.filtered(lambda move: move.country_code == "EG" and not move.pos_order_count)
        return super(AccountMove, invoices).action_post_sign_invoices()

    @api.depends("pos_order_ids.l10n_eg_edi_pos_qr")
    def _compute_eta_qr_code_str(self):
        # EXTENDS 'l10n_eg_edi_eta'
        super()._compute_eta_qr_code_str()
        for move in self.filtered(lambda m: m.country_code == "EG"):
            # sudo: the invoice can be handled by users without any access to POS orders.
            orders = move.sudo().pos_order_ids
            if ereceipt_order := orders.filtered("l10n_eg_edi_pos_qr")[:1]:
                move.l10n_eg_qr_code = ereceipt_order.l10n_eg_edi_pos_qr

    def _l10n_eg_eta_should_print_qr_code(self):
        # EXTENDS 'l10n_eg_edi_eta'
        # The QR of a sale fiscalised as an e-receipt is not gated by an e-invoice submission.
        if self.pos_order_count:
            return bool(self.l10n_eg_qr_code)
        return super()._l10n_eg_eta_should_print_qr_code()
