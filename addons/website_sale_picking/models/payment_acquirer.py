from odoo import fields, models


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    is_onsite_acquirer = fields.Boolean('Is Onsite Acquirer',
                                        default=False)

    def _get_compatible_acquirers(self, *args, sale_order_id=None, website_id=None, **kwargs):
        compatible_acquirers = super()._get_compatible_acquirers(*args, website_id=website_id, **kwargs)
        onsite_carriers = self.env['delivery.carrier'].search(
                ['&', ('website_published', '=', True), ('delivery_type', '=', 'onsite')]
            ).exists()

        # Show on site picking only if delivery carriers onsite exists

        if website_id:
            onsite_carriers = onsite_carriers.filtered_domain(['|', ('website_id', '=', website_id), ('website_id', '=', False)])
        if not onsite_carriers.exists():
            compatible_acquirers -= self.env.ref('website_sale_picking.payment_acquirer_onsite')

        # Show onsite payment only if it is a physical product
        order = self.env['sale.order'].browse(sale_order_id)
        if not any(line.product_id.type in ['consu', 'product'] for line in order.order_line):
            compatible_acquirers -= self.env.ref('website_sale_picking.payment_acquirer_onsite')

        return compatible_acquirers
