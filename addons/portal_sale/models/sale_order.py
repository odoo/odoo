# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_confirm(self):
        # fetch the partner's id and subscribe the partner to the sale order
        for order in self:
            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])
        return super(SaleOrder, self).action_confirm()

    @api.multi
    def get_signup_url(self):
        self.ensure_one()
        return self.partner_id.with_context(signup_valid=True)._get_signup_url_for_action(
            action='/mail/view',
            model=self._name,
            res_id=self.id)[self.partner_id.id]
