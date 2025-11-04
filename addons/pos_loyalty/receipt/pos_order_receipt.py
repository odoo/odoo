# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from odoo import models, _


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'
    _description = 'Point of Sale Order Receipt Generator'

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt)
        histories = self.env['loyalty.history'].search([
            ('order_id', '=', self.id),
            ('order_model', '=', 'pos.order'),
        ])

        if len(histories) > 0:
            issued = [{
                'name': history.card_id.program_id.name,
                'type': _('Won:') if history.issued > 0 else _('Spent:'),
                'points': history.issued or history.used,
            } for history in histories if history.card_id.program_id.program_type == 'loyalty']
            new_coupon = [{
                'name': history.card_id.program_id.name,
                'type': '',
                'points': history.card_id.code,
                'barcode_base64': 'data:image/png;base64,' + base64.b64encode(self.env['ir.actions.report'].barcode('Code128', history.card_id.code)).decode('utf-8'),
            } for history in histories if history.card_id.program_id.program_type == 'next_order_coupons']
            data['extra_data']['loyalties'] = issued + new_coupon

        return data
