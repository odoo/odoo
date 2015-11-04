# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    payment_method_ids = fields.One2many('payment.method', 'partner_id', string='Payment Methods')
    payment_method_count = fields.Integer(compute='_compute_payment_method_count', string='Count Payment Method')

    @api.multi
    def _compute_payment_method_count(self):
        payment_data = self.env['payment.method'].read_group([('partner_id', 'in', self.ids)], ['partner_id'], ['partner_id'])
        mapped_data = dict([(payment['partner_id'][0], payment['partner_id_count']) for payment in payment_data])
        for partner in self:
            partner.payment_method_count = mapped_data.get(partner.id, 0)
