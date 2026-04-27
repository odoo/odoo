from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleShiprocket(WebsiteSale):

    def _get_shop_payment_values(self, order, **kwargs):
        payment_values = super()._get_shop_payment_values(order, **kwargs)
        delivery_carrier = payment_values['website_sale_order'].carrier_id
        if delivery_carrier.delivery_type == "shiprocket" and delivery_carrier.shiprocket_payment_method == "cod":
            payment_methods = payment_values['payment_methods_sudo'].filtered(lambda pm: pm.code == "shiprocket_cash_on_delivery")
            payment_values['payment_methods_sudo'] = payment_methods
            payment_values['submit_button_label'] = "Place Order"
        else:
            payment_methods = payment_values['payment_methods_sudo'].filtered(lambda pm: pm.code != "shiprocket_cash_on_delivery")
            payment_values['payment_methods_sudo'] = payment_methods
        return payment_values
