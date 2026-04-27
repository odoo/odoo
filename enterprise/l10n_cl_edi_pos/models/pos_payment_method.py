# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    is_card_payment = fields.Boolean(string='Card Payment', default=False, compute='_compute_is_card_payment')

    @api.depends('journal_id')
    def _compute_is_card_payment(self):
        for pm in self:
            pm.is_card_payment = pm.journal_id.type == 'bank'

    def _load_pos_data_fields(self, config_id):
        data = super()._load_pos_data_fields(config_id)
        if self.env.company.country_id.code == 'CL':
            data += ['is_card_payment']
        return data
