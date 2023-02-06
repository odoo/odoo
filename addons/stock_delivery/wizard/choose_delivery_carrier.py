# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = 'choose.delivery.carrier'

    def _get_default_weight_uom(self):
        return self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    total_weight = fields.Float(string='Total Order Weight', related='order_id.shipping_weight', readonly=False)
    weight_uom_name = fields.Char(readonly=True, default=_get_default_weight_uom)

    @api.onchange('carrier_id', 'total_weight')
    def _onchange_carrier_id(self):
        super()._onchange_carrier_id()
        if self.delivery_type not in ('fixed', 'base_on_rule'):
            self.display_price = 0
            self.delivery_price = 0

    @api.onchange('order_id')
    def _onchange_order_id(self):
        super()._onchange_order_id(types=('fixed', 'base_on_rule'))

    @api.depends('carrier_id')
    def _compute_invoicing_message(self):
        super()._compute_invoicing_message()
        if self.carrier_id.invoice_policy == 'real':
            self.invoicing_message = _('The shipping price will be set once the delivery is done.')

    def _get_shipment_rate(self):
        carrier_with_context = self.carrier_id.with_context(order_weight=self.total_weight)
        return super()._get_shipment_rate(carrier_with_context=carrier_with_context)
