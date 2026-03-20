import { registry } from "@web/core/registry";
import * as wsTourUtils from "@website_sale/js/tours/tour_utils";
import { submitCouponCode } from "@website_sale_loyalty/../tests/tours/tour_utils";

registry.category("web_tour.tours").add('website_sale_loyalty.gift_card', {
    url: '/shop',
    steps: () => [
        // Add a small drawer to the order (50$)
        ...wsTourUtils.addToCart({ productName: "TEST - Small Drawer", expectUnloadPage: true }),
        wsTourUtils.goToCart(),
        ...submitCouponCode('GIFT_CARD'),
        {
            content: 'check gift card line',
            trigger: "#cart_products div>h6:contains(PAY WITH GIFT CARD)",
        },
        ...submitCouponCode('10PERCENT'),
        {
            content: "Check promo",
            trigger: "#cart_products div>h6:contains(10% on your order)",
        },
        {
            content: "Click on Continue Shopping",
            trigger: "div.card-body a:contains(Continue shopping)",
            run: "click",
            expectUnloadPage: true,
        },
        ...wsTourUtils.addToCart({ productName: "TEST - Gift Card", expectUnloadPage: true }),
        wsTourUtils.goToCart({quantity: 2}),
    ],
});
