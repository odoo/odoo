# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        unmatch = self.filtered(lambda so: so.carrier_id.is_mondialrelay != so.partner_shipping_id.is_mondialrelay)
        if unmatch:
            error = _('Mondial Relay mismatching between delivery method and shipping address.')
            if len(self) > 1:
                error += ' (%s)' % ','.join(unmatch.mapped('name'))
            raise UserError(error)
        return super().action_confirm()
