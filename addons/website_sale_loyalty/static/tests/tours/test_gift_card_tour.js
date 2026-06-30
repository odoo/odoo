import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('shop_sale_gift_card', {
    url: '/shop',
    steps: () => [
        // Add a small drawer to the order (50$)
        ...tourUtils.addToCart({ productName: "TEST - Small Drawer", expectUnloadPage: true }),
        tourUtils.goToCart(),
        {
            content: 'insert gift card code',
            trigger: 'form[name="coupon_code"] input[name="promo"]',
            run: "edit GIFT_CARD",
        },
        {
            content: 'validate the gift card',
            trigger: 'form[name="coupon_code"] button[type="submit"]',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: 'check gift card line',
            trigger: "#cart_products div>h6:contains(PAY WITH GIFT CARD)",
        },
        {
            content: "Insert promo",
            trigger: 'form[name="coupon_code"] input[name="promo"]',
            run: "edit 10PERCENT",
        },
        {
            content: "Validate the promo",
            trigger: 'form[name="coupon_code"] button[type="submit"]',
            run: "click",
            expectUnloadPage: true,
        },
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
        ...tourUtils.addToCart({ productName: "TEST - Gift Card", expectUnloadPage: true }),
        tourUtils.goToCart({quantity: 2}),
    ],
});
