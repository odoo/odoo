# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class BaseConfigSettings(models.TransientModel):
    _inherit = 'base.config.settings'

    @api.multi
    def set_auth_company_share_product(self):
        self.ensure_one()
        res = super(BaseConfigSettings, self).set_auth_company_share_product()
        delivery_rule = self.env.ref('delivery.delivery_comp_rule', False)
        if delivery_rule:
            delivery_rule.write({'active': not bool(self.company_share_product)})
        return res
