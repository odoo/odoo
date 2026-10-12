# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def write(self, vals):
        """ Archive pricelist when the linked currency is archived. """
        res = super().write(vals)

        if self and 'active' in vals and not vals['active']:
            self.env['product.pricelist'].search([('currency_id', 'in', self.ids)]).action_archive()

        return res
