import { registry } from '@web/core/registry';
import * as wsTourUtils from '@website_sale/js/tours/tour_utils';

registry
    .category('web_tour.tours')
    .add('website_sale_combo_configurator_single_configuration', {
        url: '/shop?search=Combo product',
        steps: () => [
            ...wsTourUtils.addToCart({ productName: "Combo product", search: false, expectUnloadPage: true }),
            wsTourUtils.goToCart(),
            // Assert that the combo configurator wasn't shown.
            ...wsTourUtils.assertCartContains({ productName: "Combo product" }),
            ...wsTourUtils.assertCartContains({ productName: "1 x Test product" }),
        ],
   });
