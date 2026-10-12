import { registry } from '@web/core/registry';
import * as tourUtils from '@website_sale/js/tours/tour_utils';

registry.category('web_tour.tours').add('website_sale.product_pricelist_qty_change', {
    steps: () => [
        tourUtils.assertProductPagePrice('20.00'),
        {
            content: "Change quantity to 5",
            trigger: 'input.quantity',
            run: 'edit 5 && click body',
        },
        tourUtils.assertProductPagePrice('10.00'),
    ],
});
