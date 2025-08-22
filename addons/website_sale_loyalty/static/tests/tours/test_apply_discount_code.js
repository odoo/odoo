import { registry } from "@web/core/registry";
import * as tourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('apply_discount_code_program_multi_rewards', {
    url: '/shop?search=Super%20Chair',
    steps: () => [
        {
            trigger: ".oe_search_found:not(:visible)",
        },
        {
            content: 'select Super Chair',
            trigger: '.oe_product_cart a:contains("Super Chair")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: 'Add Super Chair into cart',
            trigger: 'a:contains(Add to cart)',
            run: "click",
        },
        tourUtils.goToCart(),
        {
            trigger: "h4:contains(order summary)",
        },
        {
            trigger: 'form[name="coupon_code"]',
        },
        {
            content: 'insert discount code',
            trigger: 'form[name="coupon_code"] input[name="promo"]',
            run: "edit 12345",
        },
        {
            content: 'validate the promo code',
            trigger: 'form[name="coupon_code"] button[type="submit"]',
            run: "click",
            expectUnloadPage: true,
        },
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
        {
            trigger: 'form[name="coupon_code"]',
        },
        {
            content: 'insert discount code',
            trigger: 'form[name="coupon_code"] input[name="promo"]',
            run: "edit 12345",
        },
        {
            content: 'validate the promo code',
            trigger: 'form[name="coupon_code"] button[type="submit"]',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: 'check refused message',
            trigger: '.alert-danger:contains("This promo code is already applied")',
        },
    ],
});
