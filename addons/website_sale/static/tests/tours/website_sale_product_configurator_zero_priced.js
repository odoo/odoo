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
    .add('website_sale_product_configurator_zero_priced', {
        url: '/shop?search=Main product',
        steps: () => [
            ...wsTourUtils.addToCart({ productName: "Main product", search: false }),
            // Assert that the "Zero-priced" variant of the optional product can't be sold.
            ...websiteConfiguratorTourUtils.assertOptionalProductZeroPriced(
                "Optional product (Zero-priced)"
            ),
            // Add the "Zero-priced" variant by selecting the "Nonzero-priced" variant, adding it,
            // and selecting the "Zero-priced" variant again.
            configuratorTourUtils.selectAttribute("Optional product", "Price", "Nonzero-priced"),
            configuratorTourUtils.addOptionalProduct("Optional product (Nonzero-priced)"),
            configuratorTourUtils.selectAttribute("Optional product", "Price", "Zero-priced"),
            // Assert that the "Zero-priced" variant of the optional product still can't be sold.
            ...websiteConfiguratorTourUtils.assertProductZeroPriced("Optional product (Zero-priced)"),
            configuratorTourUtils.assertFooterButtonsDisabled(),
        ],
    });
