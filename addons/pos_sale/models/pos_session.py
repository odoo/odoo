# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.osv.expression import OR


class PosSession(models.Model):
    _inherit = 'pos.session'

    crm_team_id = fields.Many2one('crm.team', related='config_id.crm_team_id', string="Sales Team", readonly=True)

    def _load_data_params(self, config_id):
        params = super()._load_data_params(config_id)
        params['product.product']['fields'].extend(['invoice_policy', 'type'])
        params['product.product']['domain'] = OR([params['product.product']['domain'], [('id', '=', self.config_id.down_payment_product_id.id)]])
        return params
