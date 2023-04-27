# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def _activate_group_multi_currency(self):
        # for Sale/ POS - Multi currency flows require pricelists
        super()._activate_group_multi_currency()
        if not self.user_has_groups('product.group_product_pricelist'):
            group_user = self.env.ref('base.group_user').sudo()
            group_user._apply_group(self.env.ref('product.group_product_pricelist'))
            self.env['res.company']._activate_or_create_pricelists()
