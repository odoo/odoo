# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class product_price_list(models.TransientModel):
    _name = 'product.price_list'
    _description = 'Product Price per Unit Based on Pricelist Version'

    price_list = fields.Many2one('product.pricelist', 'PriceList', required=True)
    qty1 = fields.Integer('Quantity-1', default=1)
    qty2 = fields.Integer('Quantity-2', default=5)
    qty3 = fields.Integer('Quantity-3', default=10)
    qty4 = fields.Integer('Quantity-4', default=0)
    qty5 = fields.Integer('Quantity-5', default=0)

    @api.multi
    def print_report(self):
        """
        To get the date and print the report
        @return : return report
        """
        if (not self.env.user.company_id.logo):
            raise UserError(_("You have to set a logo or a layout for your company."))
        elif (not self.env.user.company_id.external_report_layout_id):
            raise UserError(_("You have to set your reports's header and footer layout."))

        datas = {'ids': self.env.context.get('active_ids', [])}
        res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = res and res[0] or {}
        res['price_list'] = res['price_list'][0]
        datas['form'] = res
        return self.env.ref('product.action_report_pricelist').report_action([], data=datas)
