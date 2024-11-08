# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _

from odoo.addons.sale_gelato.const import COUNTRIES_WITHOUT_POSTCODES
from odoo.addons.sale_gelato.utils import make_gelato_request


class ProviderGelato(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[('gelato', "Gelato")],
        ondelete={'gelato': lambda recs: recs.write({'delivery_type': 'fixed', 'fixed_price': 0})}
    )
    gelato_product_code = fields.Selection(
        string="Gelato Delivery Type",
        selection=[('express', "Express Delivery"), ('normal', "Standard Delivery")],
        required=True,
        default='normal',
    )

    def gelato_rate_shipment(self, order):
        """Rate gelato shipment based on ordered products, quantity and address."""
        if check_value := self.check_required_value(order.partner_id):
            return self.delivery_state(error_message=check_value)

        url = 'https://order.gelatoapis.com/v4/orders:quote'

        payload = {
            'orderReferenceId': order.id,
            'customerReferenceId': order.partner_id.id,
            'currency': order.currency_id.name,
            'allowMultipleQuotes': 'true',
            'recipient': order.get_gelato_shipping_address(),
            'products': order.get_gelato_items(),
        }
        response = make_gelato_request(company_id=order.company_id, url=url, data=payload)

        data = response.json()
        if not response.ok:
            return self.delivery_state(error_message=_("Error:\n%s", data['message']))

        delivery_price = 0
        for quote in data['quotes']:
            product_delivery_price = 0

            for method in quote['shipmentMethods']:
                if method['type'] == self.gelato_product_code:
                    if product_delivery_price == 0:
                        product_delivery_price = method['price']
                    else:
                        min(product_delivery_price, method['price'])
            if product_delivery_price == 0:
                return self.delivery_state(
                    error_message=_("This order cannot be shipped with this carrier")
                )
            delivery_price += product_delivery_price

        return self.delivery_state(True, delivery_price)

    @staticmethod
    def check_required_value(recipient):
        """
        Check if customer has all fields required for Gelato Delivery.
        """
        recipient_required_fields = ['city', 'country_id', 'street']
        if recipient.country_id.code not in COUNTRIES_WITHOUT_POSTCODES:
            recipient_required_fields.append('zip')
        res = [field for field in recipient_required_fields if not recipient[field]]
        if res:
            return _("The address of the customer is missing or wrong (Missing field(s) :\n %s)",
                     ", ".join(res).replace("_id", ""))

    @staticmethod
    def delivery_state(success=False, price=0.0, error_message=False, warning_message=False):
        return {
            'success': success,
            'price': price,
            'error_message': error_message,
            'warning_message': warning_message
        }

    def available_carriers(self, partner, order):
        res = super().available_carriers(partner, order)
        product = order.order_line.product_id.filtered(lambda p: p.sale_ok)
        if any(line.gelato_product_ref for line in product):
            return res.filtered(lambda c: c.delivery_type == 'gelato')
        else:
            return res.filtered(lambda c: c.delivery_type != 'gelato')

    def _is_available_for_order(self, order):
        """Check if both order and delivery are the gelato ones. Non-gelato orders can't use
           Gelato delivery services and Gelato Orders can only use Gelato delivery services

           :param order: current order
           :return bool: return False if delivery type and order are not compatible
        """
        is_gelato_order = bool(
            order.order_line.filtered(lambda l: l.product_id.gelato_product_ref)
        )
        is_gelato_delivery = self.delivery_type == 'gelato'
        if is_gelato_order != is_gelato_delivery:
            return False
        return super()._is_available_for_order(order)

    def gelato_send_shipping(self, pickings):
        res = []
        for p in pickings:
            res = res + [{'exact_price': p.sale_id.order_line.filtered(lambda l: l.is_delivery).price_total,
                          'tracking_number': False}]
        return res
