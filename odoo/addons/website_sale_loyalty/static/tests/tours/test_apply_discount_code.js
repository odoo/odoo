/** @odoo-module **/

import { registry } from "@web/core/registry";
import tourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('apply_discount_code_program_multi_rewards', {
    test: true,
    url: '/shop?search=Super%20Chair',
    steps: () => [
        {
            content: 'select Super Chair',
            extra_trigger: '.oe_search_found',
            trigger: '.oe_product_cart a:contains("Super Chair")',
        },
        {
            content: 'Add Super Chair into cart',
            trigger: 'a:contains(Add to cart)',
        },
        tourUtils.goToCart(),
        {
            content: 'insert discount code',
            extra_trigger: 'form[name="coupon_code"]',
            trigger: 'form[name="coupon_code"] input[name="promo"]',
            run: 'text 12345'
        },
        {
            content: 'validate the promo code',
            trigger: 'form[name="coupon_code"] .a-submit',
        },
        {
            content: 'check reward',
            trigger: '.alert:contains("10% on Super Chair")',
            isCheck: true,
        },
        {
            content: 'claim reward',
            trigger: '.alert:contains("10% on Super Chair") .btn:contains("Claim")',
        },
        {
            content: 'check claimed reward',
            trigger: 'div>strong:contains("10% on Super Chair")',
            isCheck: true,
        },
        // Try to reapply the same promo code
        {
            content: 'insert discount code',
            extra_trigger: 'form[name="coupon_code"]',
            trigger: 'form[name="coupon_code"] input[name="promo"]',
            run: 'text 12345'
        },
        {
            content: 'validate the promo code',
            trigger: 'form[name="coupon_code"] .a-submit',
        },
        {
            content: 'check refused message',
            trigger: '.alert-danger:contains("This promo code is already applied")',
            isCheck: true,
        },
    ],
});
