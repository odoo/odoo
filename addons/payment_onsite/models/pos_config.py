# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from ..utils import _format_carrier_name
class PosConfigOnSite(models.Model):
    _inherit = 'pos.config'

    delivery_carrier_id = fields.Many2one('delivery.carrier', string="Shipping method",
                                          readonly=True,
                                          store=True)

    def _get_delivery_product(self):
        return self.env.ref('payment_onsite.onsite_delivery_product')

    def _get_acquirer(self):
        return self.env.ref('payment_onsite.payment_acquirer_onsite')

    def _create_carriers(self, names):
        product = self._get_delivery_product()
        return self.env['delivery.carrier'].sudo().create([{
            'name': _format_carrier_name(name),
            'product_id': product.id,
            'delivery_type': 'onsite'
        } for name in names])

    @api.model_create_multi
    def create(self, vals_list):
        pos_configs = super().create(vals_list)
        onsite_acquirer = self._get_acquirer()

        pos_no_carriers = pos_configs.filtered(lambda p: not p.delivery_carrier_id)
        carriers = self._create_carriers(pos_no_carriers.mapped('name'))

        for pos_config, carrier in zip(pos_no_carriers, carriers):
            pos_config.delivery_carrier_id = carrier
        onsite_acquirer.carrier_ids |= carriers
        return pos_configs

    def write(self, vals):
        if 'name' in vals and self.delivery_carrier_id:
            self.delivery_carrier_id.name = _format_carrier_name(vals['name'])
        return super().write(vals)

    def unlink(self):
        self.delivery_carrier_id.unlink()  # No point in keeping delivery carriers for deleted pos
        return super().unlink()
