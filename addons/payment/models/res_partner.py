# coding: utf-8

from odoo import api, fields, models


class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    payment_token_ids = fields.One2many('payment.token', 'partner_id', 'Payment Tokens')
    payment_token_count = fields.Integer('Count Payment Token', compute='_compute_payment_token_count')

    @api.depends('payment_token_ids')
    def _compute_payment_token_count(self):
        payment_data = self.env['payment.token'].read_group([
            ('partner_id', 'in', self.ids)], ['partner_id'], ['partner_id'])
        mapped_data = dict([(payment['partner_id'][0], payment['partner_id_count']) for payment in payment_data])
        for partner in self:
            partner.payment_token_count = mapped_data.get(partner.id, 0)
