import { registry } from '@web/core/registry';
import configuratorTourUtils from '@sale/js/tours/combo_configurator_tour_utils';
import * as wsTourUtils from '@website_sale/js/tours/tour_utils';

registry
    .category('web_tour.tours')
    .add('website_sale_renting_combo_configurator', {
        url: '/shop?search=Combo product',
        steps: () => [
            ...wsTourUtils.addToCart({ productName: "Combo product", search: false, expectUnloadPage: true }),
            // Assert that the rental price and duration is correct.
            configuratorTourUtils.assertPrice('5.00'),
            configuratorTourUtils.assertPriceInfo("1 Hour"),
            configuratorTourUtils.selectComboItem("Test Product"),
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
