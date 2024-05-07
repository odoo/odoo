from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _create_invoice(self, move_vals):
        move = super()._create_invoice(move_vals)

        if move.move_type != 'out_refund':
            return move

        if move.l10n_es_is_simplified:
            move.l10n_es_tbai_refund_reason = 'R5'
        else:
            move.l10n_es_tbai_refund_reason = 'R4'

        return move

    def get_l10n_es_pos_tbai_qrurl(self):
        """ This function manually triggers the send & print, so that we can retrieve the generated QR code
        from the post response and transfer it to JS and eventually the Order Receipt XML. """
        self.ensure_one()
        invoice = self.account_move

        if invoice.l10n_es_tbai_is_required:
            invoice.action_send_and_print()
            return invoice.l10n_es_tbai_post_document_id._get_tbai_qr()
