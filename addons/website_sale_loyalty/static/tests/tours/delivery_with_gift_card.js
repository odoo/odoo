import { registry } from "@web/core/registry";
import * as wsTourUtils from "@website_sale/js/tours/tour_utils";
import { payWithGiftCard } from "@website_sale_loyalty/../tests/tours/tour_utils";

registry.category("web_tour.tours").add('website_sale_loyalty.delivery_with_gift_card', {
    steps: () => [
        ...wsTourUtils.addToCartFromProductPage(),
        wsTourUtils.goToCart(1),
        wsTourUtils.goToCheckout(),
        wsTourUtils.selectDeliveryCarrier('delivery1'),
        wsTourUtils.confirmOrder(),
        ...wsTourUtils.assertCartAmounts({
            total: '105.00',
            delivery: '5.00'
        }),
        // The gift card pays the order, delivery fees included.
        ...payWithGiftCard("123456", "105.00"),
        {
            content: "The order is paid",
            trigger: 'div h3:contains("Thank you for your order.")',
        },
    ]
});
