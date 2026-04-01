import { registry } from "@web/core/registry";
import * as wsTourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('shop_sale_loyalty_delivery', {
    url: '/shop',
    steps: () => [
        ...wsTourUtils.addToCart({ productName: "Plumbus", expectUnloadPage: true }),
        wsTourUtils.goToCart(1),
        wsTourUtils.goToCheckout(),
        {
            content: "select delivery method 1",
            trigger: "li label:contains(delivery1)",
            run: "click",
        },
        {
            content: "Enter gift card code",
            trigger: "form[name='coupon_code'] input[name='promo']",
            run: "edit 123456",
        },
        {
            content: "click on 'Apply'",
            trigger: 'form[name="coupon_code"] button[type="submit"]',
            run: "click",
            expectUnloadPage: true,
        },
        wsTourUtils.confirmOrder(),
        ...wsTourUtils.assertCartAmounts({
            total: '0.00',
            delivery: '5.00'
        }),
    ]
});
