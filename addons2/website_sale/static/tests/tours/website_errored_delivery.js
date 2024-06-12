/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('check_errored_delivery', {
    test: true,
    url: '/shop?search=office chair black',
    steps: () => [
        {
            content: "select office chair black",
            trigger: '.oe_product_cart a:contains("Office Chair Black TEST")',
        },
        {
            content: "click on add to cart",
            trigger: '#product_details #add_to_cart',
        },
        tourUtils.goToCart(),
        {
            content: "go to checkout",
            extra_trigger: '#cart_products input.js_quantity:propValue(1)',
            trigger: 'a[href*="/shop/checkout"]',
        },
        {
            trigger: 'button[name="o_payment_submit_button"]:disabled',
            isCheck: true,
        }
    ]});
