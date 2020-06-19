# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_tax_id = fields.Many2one('account.tax', string="Default Sale Tax", related='company_id.account_sale_tax_id', readonly=False)
    module_pos_mercury = fields.Boolean(string="Vantiv Payment Terminal", help="The transactions are processed by Vantiv. Set your Vantiv credentials on the related payment method.")
    module_pos_adyen = fields.Boolean(string="Adyen Payment Terminal", help="The transactions are processed by Adyen. Set your Adyen credentials on the related payment method.")
    module_pos_six = fields.Boolean(string="Six Payment Terminal", help="The transactions are processed by Six. Set the IP address of the terminal on the related payment method.")
    update_stock_quantities = fields.Selection(related="company_id.point_of_sale_update_stock_quantities", readonly=False)

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        if not self.group_product_pricelist:
            configs = self.env['pos.config'].search([('use_pricelist', '=', True)])
            for config in configs:
                config.use_pricelist = False
