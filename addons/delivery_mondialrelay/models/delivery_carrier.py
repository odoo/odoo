# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class DeliveryCarrierMondialRelay(models.Model):
    _inherit = 'delivery.carrier'

    is_mondialrelay = fields.Boolean(compute='_compute_is_mondialrelay')
    mondialrelay_brand = fields.Char(string='Brand Code', default='BDTEST  ', groups="base.group_system")
    mondialrelay_packagetype = fields.Char(default="24R", groups="base.group_system")  # Advanced

    @api.depends('product_id.default_code')
    def _compute_is_mondialrelay(self):
        for c in self:
            c.is_mondialrelay = c.product_id.default_code == "MR"

    def fixed_get_tracking_link(self, picking):
        return self.base_on_rule_get_tracking_link(picking)

    def base_on_rule_get_tracking_link(self, picking):
        if self.is_mondialrelay:
            return 'https://www.mondialrelay.com/public/permanent/tracking.aspx?ens=%(brand)s&exp=%(track)s&language=%(lang)s' % {
                'brand': picking.carrier_id.mondialrelay_brand,
                'track': picking.carrier_tracking_ref,
                'lang': (picking.partner_id.lang or 'fr').split('_')[0],
            }
        return super().base_on_rule_get_tracking_link(picking)
