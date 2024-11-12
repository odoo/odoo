# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def _activate_group_multi_currency(self):
        # for Sale/ POS - Multi currency flows require pricelists
        super()._activate_group_multi_currency()
        if not self.env.user.has_group('product.group_product_pricelist'):
            group_user = self.env.ref('base.group_user').sudo()
            group_user._apply_group(self.env.ref('product.group_product_pricelist'))
            self.env['res.company']._activate_or_create_pricelists()

    def write(self, vals):
        """ Archive pricelist when the linked currency is archived. """
        res = super().write(vals)

        if self and 'active' in vals and not vals['active']:
            self.env['product.pricelist'].search([('currency_id', 'in', self.ids)]).action_archive()

        return res
