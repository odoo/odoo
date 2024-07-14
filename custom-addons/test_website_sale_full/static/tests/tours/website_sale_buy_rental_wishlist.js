/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('shop_buy_rental_product_wishlist', {
    test: true,
    url: '/shop?search=Computer',
    steps: () => [
        {
            content: "click on add to wishlist",
            trigger: '.o_add_wishlist',
        },
        {
            content: "go to wishlist",
            extra_trigger: 'a[href="/shop/wishlist"] .badge.text-bg-primary:contains(1)',
            trigger: 'a[href="/shop/wishlist"]',
        },
        {
            content: "click on add to cart",
            trigger: '.o_wish_add',
        },
        tourUtils.goToCart({quantity: 1}),
        {
            content: "Verify there is a Computer",
            trigger: '#cart_products div a h6:contains("Computer")',
            isCheck: true,
        },
        {
            content: "Verify there are 1 quantity of Computers",
            trigger: '#cart_products div div.css_quantity input[value=1]',
            isCheck: true,
        },
        {
            content: "go to checkout",
            extra_trigger: '#cart_products .oe_currency_value:contains(75.00)',
            trigger: 'a[href*="/shop/checkout"]',
        },
        {
            content: "verify checkout page",
            trigger: 'span div.o_wizard_step_active:contains("Payment")',
            isCheck: true,
        },
    ]
});
