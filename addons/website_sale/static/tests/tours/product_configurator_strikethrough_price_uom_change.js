import { registry } from '@web/core/registry';
import configuratorTourUtils from '@sale/js/tours/product_configurator_tour_utils';
import websiteConfiguratorTourUtils from '@website_sale/js/tours/product_configurator_tour_utils';

registry
    .category('web_tour.tours')
    .add('website_sale.product_configurator_strikethrough_price_uom_change', {
        steps: () => [
            {
                trigger: '.oe_product_cart:contains("Packaged product")',
                run: `hover && click .oe_product_cart:contains("Packaged product") button[name="add_to_cart"]`,
            },
            configuratorTourUtils.assertProductPrice("Packaged product", '100.00'),
            websiteConfiguratorTourUtils.assertProductStrikethroughPrice(
                "Packaged product", '200.00'
            ),
            configuratorTourUtils.setProductUoM("Packaged product", "Pack of 6"),
            configuratorTourUtils.assertProductPrice("Packaged product", '600.00'),
            websiteConfiguratorTourUtils.assertProductStrikethroughPrice(
                "Packaged product", '1,200.00'
            ),
        ],
    });
