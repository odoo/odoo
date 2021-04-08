# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.exceptions import AccessError


class PosConfig(models.Model):
    _inherit = 'pos.config'


    crm_team_id = fields.Many2one(
        'crm.team', string="Sales Team", ondelete="set null",
        help="This Point of sale's sales will be related to this Sales Team.")
    down_payment_product_id = fields.Many2one('product.product',
        string="Down Payment Product",
        help="This product will be used as down payment on a sale order.")

    @api.onchange('company_id')
    def _get_default_pos_team(self):
        default_sale_team = self.env.ref('sales_team.pos_sales_team', raise_if_not_found=False)
        if default_sale_team and (not default_sale_team.company_id or default_sale_team.company_id == self.company_id):
            self.crm_team_id = default_sale_team
        else:
            self.crm_team_id = self.env['crm.team'].search(['|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)], limit=1)
