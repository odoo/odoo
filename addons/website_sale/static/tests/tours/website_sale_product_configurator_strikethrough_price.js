<<<<<<< master
||||||| 23c39ea45257d3dc0c5c69af8875709739aa90c3
/** @odoo-module **/

import { registry } from '@web/core/registry';
=======
import { registry } from '@web/core/registry';
>>>>>>> c48c1c693d548b2bb42aaea67e2487e43385ca31
import configuratorTourUtils from '@sale/js/tours/product_configurator_tour_utils';
import { registry } from '@web/core/registry';
import websiteConfiguratorTourUtils from '@website_sale/js/tours/product_configurator_tour_utils';
import * as wsTourUtils from '@website_sale/js/tours/tour_utils';

registry
    .category('web_tour.tours')
    .add('website_sale_product_configurator_strikethrough_price', {
        url: '/shop?search=Main product',
        steps: () => [
            ...wsTourUtils.addToCart({ productName: "Main product", search: false }),
            configuratorTourUtils.assertProductPrice("Main product", '55.00'),
            websiteConfiguratorTourUtils.assertProductStrikethroughPrice("Main product", '110.00'),
            configuratorTourUtils.assertOptionalProductPrice("Optional product", '5.50'),
            websiteConfiguratorTourUtils.assertOptionalProductStrikethroughPrice(
                "Optional product", '10.00'
            ),
        ],
   });
