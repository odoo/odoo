# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.tools.image import image_data_uri
from odoo.tools import float_round


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'
    _description = 'Point of Sale Order Receipt Generator'

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt)
        loyalties, new_coupons = [], []
        histories = self.env['loyalty.history'].search([('order_id', '=', self.id), ('order_model', '=', 'pos.order')])
        for history in histories:
            program_type = history.card_id.program_id.program_type
            if program_type == 'loyalty':
                for field, label in [('issued', _('Won:')), ('used', _('Spent:'))]:
                    amount = history[field]
                    if amount > 0:
                        loyalties.append({
                            'name': history.card_id.program_id.portal_point_name,
                            'type': label,
                            'points': float_round(amount, 2),
                        })

                loyalties.append({
                    'name': history.card_id.program_id.portal_point_name,
                    'type': _('Balance:'),
                    'points': float_round(history.card_id.points, 2),
                })

            elif program_type == 'next_order_coupons':
                new_coupons.append({
                    'name': history.card_id.program_id.name,
                    'code': history.card_id.code,
                    'expiration_date': history.card_id.expiration_date,
                    'barcode_base64': image_data_uri(self.env['ir.actions.report'].barcode('Code128', history.card_id.code, quiet=False)),
                })

        data['extra_data']['loyalties'] = loyalties
        data['extra_data']['new_coupons'] = new_coupons

        return data
