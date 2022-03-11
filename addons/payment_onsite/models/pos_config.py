from odoo import models, fields, api, _


class PosConfigOnSite(models.Model):
    _inherit = 'pos.config'
    delivery_carrier_id = fields.Many2one('delivery.carrier', string="Shipping method",
                                          readonly=True,
                                          compute='_compute_delivery_carrier',
                                          store=True)

    @api.depends('name')
    def _compute_delivery_carrier(self):
        # TODO : Fix xml id that does not exist on module install
        product = self.env.ref('payment_onsite.onsite_delivery_product')
        for record in self:
            if not record.delivery_carrier_id:
                record.delivery_carrier_id = self.env['delivery.carrier'].create({
                    'name': f"{record.name} - {_('on site')}",
                    'product_id': product.id
                })
            else:
                record.delivery_carrier_id.name = f"{record.name} - on site"
