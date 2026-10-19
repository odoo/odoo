# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.tools import float_round
from odoo.tools.image import image_data_uri


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'

    def _is_item_count_excluded_line(self, line):
        return super()._is_item_count_excluded_line(line) or line.is_reward_line

    def order_receipt_generate_data(self, basic_receipt=False):
        """Add the loyalty points summary and issued-coupon barcodes to the receipt.

        The JS counterpart is ``GeneratePrinterData._generateLoyaltyReceiptData``; both must
        produce the same rows (won/spent/balance per loyalty program, and the ``new_coupons``
        barcodes) so the frontend and backend receipts match.
        """
        data = super().order_receipt_generate_data(basic_receipt)
        loyalties = []
        histories = self.env['loyalty.history'].search([
            ('order_model', '=', 'pos.order'),
            ('order_id', '=', self.id),
        ])
        # Spending points takes one line per award drawn from, so a card can hold several
        # rows for the same order. The receipt shows one figure per card, not per row.
        for card, card_histories in histories.grouped('card_id').items():
            program = card.program_id
            if program.program_type != 'loyalty':
                continue
            for points, label in [
                (sum(card_histories.mapped('issued')), _("Won:")),
                (sum(card_histories.mapped('used')), _("Spent:")),
            ]:
                if points > 0:
                    loyalties.append({
                        'name': program.portal_point_name,
                        'type': label,
                        'points': float_round(points, precision_rounding=0.01),
                    })
            loyalties.append({
                'name': program.portal_point_name,
                'type': _("Balance:"),
                'points': float_round(card.points, precision_rounding=0.01),
            })
        data['extra_data']['loyalties'] = loyalties

        new_coupons = []
        coupon_cards = self.env['loyalty.card'].search([
            ('source_pos_order_id', '=', self.id),
        ])
        for card in coupon_cards.filtered(lambda c: c._is_new_receipt_coupon(self)):
            new_coupons.append({
                'name': card.program_id.name,
                'code': card.code,
                'expiration_date': card.expiration_date,
                'barcode_base64': image_data_uri(
                    self.env['ir.actions.report'].barcode('Code128', card.code, quiet=False)
                ),
            })
        data['extra_data']['new_coupons'] = new_coupons
        return data
