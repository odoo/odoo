/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from '@website_sale/js/tours/tour_utils';
import { TourError } from "@web_tour/tour_service/tour_utils";


registry.category("web_tour.tours").add('shop_sale_ewallet', {
    test: true,
    url: '/shop',
    steps: () => [
        // Add a small drawer to the order (50$)
        ...tourUtils.addToCart({productName: "TEST - Small Drawer"}),
        tourUtils.goToCart(),
        {
            trigger: 'a:contains("Pay with eWallet")',
            extra_trigger: 'form[name="claim_reward"]',
            run() {
                const rewards = document.querySelectorAll('form[name="claim_reward"]');
                if (rewards.length === 1) {
                    this.$anchor.click();
                } else {
                    throw new TourError(`Expected 1 claimable reward, got: ${rewards.length}`);
                }
            },
        },
        tourUtils.goToCheckout(),
        tourUtils.pay(),
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
