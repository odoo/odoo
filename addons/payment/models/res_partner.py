# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    payment_token_ids = fields.One2many(
        string="Payment Tokens", comodel_name='payment.token', inverse_name='partner_id')
    payment_token_count = fields.Integer(
        string="Payment Token Count", compute='_compute_payment_token_count')

    @api.depends('payment_token_ids')
    def _compute_payment_token_count(self):
        payments_data = self.env['payment.token']._aggregate(
            [('partner_id', 'in', self.ids)], ['*:count'], ['partner_id']
        )
        for partner in self:
            partner.payment_token_count = payments_data.get_agg(partner.id, '*:count', 0)
