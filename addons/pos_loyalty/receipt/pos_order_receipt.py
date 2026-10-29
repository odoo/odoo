# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from collections import defaultdict

from odoo import models, _
from odoo.tools import float_round


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'
    _description = 'Point of Sale Order Receipt Generator'

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt)
        loyalty_data = self._get_loyalty_data([self.id]).get(self.id, {})

        data['extra_data']['loyalties'] = loyalty_data.get('loyalties', [])
        data['extra_data']['new_coupons'] = loyalty_data.get('new_coupons', [])
        return data

    def _get_loyalty_data(self, order_ids):
        loyalty_data = defaultdict(lambda: {'loyalties': [], 'new_coupons': []})
        histories = self.env['loyalty.history'].search([('order_id', 'in', order_ids), ('order_model', '=', 'pos.order')])

        for history in histories:
            card = history.card_id
            program = card.program_id
            order_data = loyalty_data[history.order_id]

            if program.program_type == 'loyalty':
                for field, label in [('issued', _('Won:')), ('used', _('Spent:'))]:
                    amount = history[field]
                    if amount > 0:
                        order_data['loyalties'].append({
                            'name': program.portal_point_name,
                            'type': label,
                            'points': float_round(amount, 2),
                        })

                order_data['loyalties'].append({
                    'name': program.portal_point_name,
                    'type': _('Balance:'),
                    'points': float_round(card.points, 2),
                })

            elif program.program_type == 'next_order_coupons':
                order_data['new_coupons'].append({
                    'program_name': program.name,
                    'code': card.code,
                    'expiration_date': card.expiration_date,
                    'barcode_base64': 'data:image/png;base64,' + base64.b64encode(self.env['ir.actions.report'].barcode('Code128', card.code, quiet=False)).decode('utf-8'),
                })

        return loyalty_data
