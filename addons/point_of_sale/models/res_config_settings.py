# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_tax_id = fields.Many2one('account.tax', string="Default Sale Tax", related='company_id.account_sale_tax_id', readonly=False)
    module_pos_mercury = fields.Boolean(string="Integrated Card Payments", help="The transactions are processed by Vantiv. Set your Vantiv credentials on the related payment journal.")
    pos_sales_price = fields.Boolean("Multiple Product Prices", config_parameter='point_of_sale.pos_sales_price')
    pos_pricelist_setting = fields.Selection([
        ('percentage', 'Multiple prices per product (e.g. customer segments, currencies)'),
        ('formula', 'Price computed from formulas (discounts, margins, roundings)')
        ], string="POS Pricelists", config_parameter='point_of_sale.pos_pricelist_setting')

    @api.onchange('pos_sales_price')
    def _onchange_pos_sales_price(self):
        if not self.pos_sales_price:
            self.pos_pricelist_setting = False
        if self.pos_sales_price and not self.pos_pricelist_setting:
            self.pos_pricelist_setting = 'percentage'

    @api.onchange('pos_pricelist_setting')
    def _onchange_pos_pricelist_setting(self):
        self.sale_pricelist_setting_sync(self.pos_pricelist_setting)
        if self.pos_pricelist_setting == 'percentage':
            self.update({
                'group_product_pricelist': True,
                'group_sale_pricelist': True,
                'group_pricelist_item': False,
            })
        elif self.pos_pricelist_setting == 'formula':
            self.update({
                'group_product_pricelist': False,
                'group_sale_pricelist': True,
                'group_pricelist_item': True,
            })
        else:
            self.update({
                'group_product_pricelist': False,
                'group_sale_pricelist': False,
                'group_pricelist_item': False,
            })

    def pos_pricelist_setting_sync(self, sale_pricelist_setting):
        if sale_pricelist_setting == 'fixed':
            self.pos_sales_price = False
            self.pos_pricelist_setting = False
        else:
            self.pos_sales_price = True
            self.pos_pricelist_setting = sale_pricelist_setting
