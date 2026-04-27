import { registry } from '@web/core/registry';
import configuratorTourUtils from '@sale/js/tours/product_configurator_tour_utils';
import * as wsTourUtils from '@website_sale/js/tours/tour_utils';

registry
    .category('web_tour.tours')
    .add('website_sale_renting_product_configurator', {
        url: '/shop?search=Main product',
        steps: () => [
            ...wsTourUtils.addToCart({ productName: "Main product", search: false, expectUnloadPage: true }),
            // Assert that the rental prices and durations are correct.
            configuratorTourUtils.assertProductPrice("Main product", '5.00'),
            configuratorTourUtils.assertProductPriceInfo("Main product", "1 Hour"),
            configuratorTourUtils.assertOptionalProductPrice("Optional product", '6.00'),
            configuratorTourUtils.assertOptionalProductPriceInfo("Optional product", "1 Hour"),
            {
                content: "Proceed to checkout",
                trigger: 'button:contains(Proceed to Checkout)',
                run: 'click',
                expectUnloadPage: true,
            },
            {
                content: "Verify the rental price and duration in the cart",
                trigger: 'div.o_cart_product div:contains(5.00 / 1 Hour)',
            },
        ],
   });
