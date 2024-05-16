/** @odoo-module **/

import { registry } from "@web/core/registry";
import wsTourUtils from "@website_sale/js/tours/tour_utils";
import { TourError } from "@web_tour/tour_service/tour_utils";


registry.category("web_tour.tours").add('shop_sale_ewallet', {
    test: true,
    url: '/shop',
    steps: () => [
        // Add a small drawer to the order (50$)
        ...wsTourUtils.addToCart({productName: "TEST - Small Drawer"}),
        wsTourUtils.goToCart(),
        {
            trigger: 'a:contains("Pay with eWallet")',
            run: "click",
        },
        {
            content: 'Checkout',
            trigger: 'a[name="website_sale_main_button"]',
            run: "click",
        },
        {
            content: 'Confirm Order',
            trigger: 'button[name="o_payment_submit_button"]',
            run: "click",
        },
        {
            trigger: 'div[id="introduction"] h2:contains("Sales Order")'
        },
        {
            trigger: 'a[href="/shop/cart"]',
            run: function() {
                const cartQuantity = document.querySelector('.my_cart_quantity');
                if (cartQuantity.textContent !== '0'){
                    throw new TourError('cart should be empty and reset after an order is paid using ewallet')
                }
            }
        },
    ],
});
