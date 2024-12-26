import { registry } from '@web/core/registry';
import * as wsTourUtils from '@website_sale/js/tours/tour_utils';

registry
    .category('web_tour.tours')
    .add('website_sale_combo_configurator_single_configurable_item', {
        url: '/shop?search=Combo product',
        steps: () => [
            ...wsTourUtils.addToCart({ productName: "Combo product", search: false }),
            {
                content: "Assert that the combo configurator is shown",
                trigger: '.sale-combo-configurator-dialog',
            },
        ],
   });
