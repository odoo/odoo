from odoo import fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    l10n_sa_invoice_qr_code_str = fields.Char(related="account_move.l10n_sa_qr_code_str", string="ZATCA QR Code")
    l10n_sa_invoice_edi_state = fields.Selection(related="account_move.l10n_sa_edi_state", string="Electronic invoicing")

    def _is_settle_or_deposit_order(self):
        self.ensure_one()
        """
        Check if the invoice is linked to a POS settlement order
        Only available when pos_settle_due module is installed
        """
        if not hasattr(self.env['pos.order.line'], '_is_settle_or_deposit'):
            return False
        return any(line._is_settle_or_deposit() for line in self.lines)

    def _l10n_sa_is_phase_2_applicable(self, check_document=True):
        self.ensure_one()
        return self._l10n_sa_is_phase_1_applicable() and self.state in ('done', 'paid') and \
               self.journal_id._l10n_sa_ready_to_submit_einvoices() and (self.l10n_sa_edi_document_id or not check_document)

    def _get_l10n_sa_journal(self):
        self.ensure_one()
        return self.session_id.config_id.journal_id
