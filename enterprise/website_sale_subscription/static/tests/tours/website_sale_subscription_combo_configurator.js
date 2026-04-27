import { registry } from '@web/core/registry';
import configuratorTourUtils from '@sale/js/tours/combo_configurator_tour_utils';
import * as wsTourUtils from '@website_sale/js/tours/tour_utils';

registry
    .category('web_tour.tours')
    .add('website_sale_subscription_combo_configurator', {
        url: '/shop?search=Combo product',
        steps: () => [
            ...wsTourUtils.addToCart({ productName: "Combo product", search: false, expectUnloadPage: true }),
            // Assert that the subscription price and plan is correct.
            configuratorTourUtils.assertPrice('5.00'),
            configuratorTourUtils.assertPriceInfo("per week"),
            configuratorTourUtils.selectComboItem("Test Product"),
            {
                content: "Proceed to checkout",
                trigger: 'button:contains(Proceed to Checkout)',
                run: 'click',
                expectUnloadPage: true,
            },
            {
                content: "Verify the subscription price in the cart",
                trigger: 'div[name="website_sale_cart_line_price"]:contains(5.00)',
            },
            {
                content: "Verify the subscription plan in the cart",
                trigger: 'div[name="website_sale_cart_line_price"]:contains(per week)',
            },
        ],
   });
