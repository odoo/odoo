# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _

from odoo.addons.sale_gelato_connector.const import COUNTRIES_WITHOUT_POSTCODES
from odoo.addons.sale_gelato_connector.utils import make_gelato_request


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
        request = make_gelato_request(company_id=order.company_id, url=url, data=payload)

        data = request.json()
        if not request.ok:
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

    def available_carriers(self, partner, sale_order):
        res = super().available_carriers(partner, sale_order)
        product = sale_order.order_line.product_id.filtered(lambda p: p.sale_ok)
        if any(line.gelato_reference for line in product):
            return res.filtered(lambda c: c.delivery_type == 'gelato')
        else:
            return res.filtered(lambda c: c.delivery_type != 'gelato')

    def _is_available_for_order(self, order):

        if ((any(line.product_id.gelato_reference for line in order.order_line) and self.delivery_type != 'gelato')
                or all(not line.product_id.gelato_reference for line in order.order_line) and self.delivery_type == 'gelato'):
            return False

        # elif all(not line.product_id.gelato_reference for line in
        #          order.order_line) and self.delivery_type == 'gelato':
        #     return False

        return super()._is_available_for_order(order)
