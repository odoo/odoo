# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, models
from odoo.exceptions import UserError


class EstateProperty(models.Model):
    _inherit = 'estate.property'

    def action_sold(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(self.env._('Accept an offer before selling the property.'))
        result = super().action_sold()
        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_line_ids': [
                Command.create({
                    'name': self.env._('Real estate commission'),
                    'quantity': 1,
                    'price_unit': self.selling_price * 0.06,
                }),
                Command.create({
                    'name': self.env._('Administrative fees'),
                    'quantity': 1,
                    'price_unit': 100.0,
                }),
            ],
        })
        return result
