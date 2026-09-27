import { registry } from "@web/core/registry";
import * as wsTourUtils from "@website_sale/js/tours/tour_utils";
import { submitCouponCode } from "@website_sale_loyalty/../tests/tours/tour_utils";

registry.category("web_tour.tours").add('website_sale_loyalty.delivery_with_gift_card', {
    steps: () => [
        ...wsTourUtils.addToCartFromProductPage(),
        wsTourUtils.goToCart(1),
        wsTourUtils.goToCheckout(),
        wsTourUtils.selectDeliveryCarrier('delivery1'),
        ...submitCouponCode('123456'),
        wsTourUtils.confirmOrder(),
        ...wsTourUtils.assertCartAmounts({
            total: '0.00',
            delivery: '5.00'
        }),
    ]
});
