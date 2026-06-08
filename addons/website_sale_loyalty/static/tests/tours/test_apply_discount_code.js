import { registry } from "@web/core/registry";
import * as wsTourUtils from "@website_sale/js/tours/tour_utils";
import { submitCouponCode } from "@website_sale_loyalty/../tests/tours/tour_utils";

registry.category("web_tour.tours").add('website_sale_loyalty.apply_discount_code_multi_rewards', {
    steps: () => [
        ...wsTourUtils.addToCartFromProductPage(),
        wsTourUtils.goToCart(),
        {
            trigger: "h4:contains(order summary)",
        },
        ...submitCouponCode('12345'),
        {
            content: 'check reward',
            trigger: '.alert:contains("10% on Super Chair")',
        },
        {
            content: 'claim reward',
            trigger: '.alert:contains("10% on Super Chair") .btn:contains("Claim")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "check claimed reward",
            trigger:
                "#cart_products.js_cart_lines .o_cart_product h6:contains(10% on Super Chair)",
        },
        // Try to reapply the same promo code
        ...submitCouponCode('12345'),
        {
            content: 'check refused message',
            trigger: '.alert-danger:contains("This promo code is already applied")',
        },
    ],
});
