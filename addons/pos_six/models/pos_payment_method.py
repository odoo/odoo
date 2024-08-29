# coding: utf-8
from odoo.addons import point_of_sale
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class PosPaymentMethod(models.Model, point_of_sale.PosPaymentMethod):

    def _get_payment_terminal_selection(self):
        return super(PosPaymentMethod, self)._get_payment_terminal_selection() + [('six', 'SIX')]

    six_terminal_ip = fields.Char('Six Terminal IP')

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['six_terminal_ip']
        return params
