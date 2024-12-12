import { registry } from '@web/core/registry';
import * as tourUtils from '@website_sale/js/tours/tour_utils';

let image_src;
registry.category('web_tour.tours').add('website_sale_shop_products', {
    url: '/shop',
    steps: () => [
        ...tourUtils.searchProduct("Test"),
        {
            trigger: '.o_wsale_product_attribute div:last',
            run(helpers) {
                helpers.hover(helpers.anchor);
                helpers.hover('.o_wsale_product_attribute div:last');
                image_src = document.querySelector(".oe_product_image img").src;
            },
        },
        {
            trigger: '.o_wsale_product_attribute div:first',
            run(helpers) {
                helpers.hover(helpers.anchor);
                helpers.hover(".o_wsale_product_attribute div:first");
                if (document.querySelector(".oe_product_image img").src === image_src) {
                    console.error("Image did not change on hover");
                }
            }
        },
    ],
});
