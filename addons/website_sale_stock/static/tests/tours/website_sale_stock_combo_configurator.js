import { registry } from '@web/core/registry';
import configuratorTourUtils from '@sale/js/tours/combo_configurator_tour_utils';
import * as wsTourUtils from '@website_sale/js/tours/tour_utils';
import stockConfiguratorTourUtils from '@website_sale_stock/js/tours/combo_configurator_tour_utils';

registry
    .category('web_tour.tours')
    .add('website_sale_stock_combo_configurator', {
        url: '/shop?search=Combo product',
        steps: () => [
            ...wsTourUtils.addToCart({ productName: "Combo product", search: false, expectUnloadPage: true }),
            configuratorTourUtils.assertQuantity(1),
            // Assert that it's impossible to add less than 1 product.
            configuratorTourUtils.setQuantity(0),
            configuratorTourUtils.assertQuantity(1),
            {
                content: "Verify that the quantity decrease button is disabled",
                trigger: `
                    .sale-combo-configurator-dialog
                    button[name=sale_quantity_button_minus]:disabled
                `,
            },
            // Assert that an error is shown if the requested quantity isn't available.
            configuratorTourUtils.setQuantity(3),
            stockConfiguratorTourUtils.assertQuantityNotAvailable("Test product"),
            // Assert that a warning is shown if all available quantity is selected.
            configuratorTourUtils.setQuantity(2),
            configuratorTourUtils.selectComboItem("Test product"),
            stockConfiguratorTourUtils.assertAllQuantitySelected("Test product"),
            // Assert that it's impossible to add more products than available.
            configuratorTourUtils.setQuantity(3),
            configuratorTourUtils.assertQuantity(2),
            {
                content: "Verify that the quantity increase button is disabled",
                trigger: `
                    .sale-combo-configurator-dialog
                    button[name=sale_quantity_button_plus]:disabled
                `,
            },
        ],
   });

registry.category("web_tour.tours").add("test_website_sale_stock_max_combo", {
    steps: () => [
        {
            content: "Select ComboProduct",
            trigger: ".oe_product_cart:first a:contains('ComboProduct')",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "VariantMixin has set the maximum",
            trigger: "input[name=add_qty][data-max='2']",
        },
        {
            content: "Add one quantity",
            trigger: ".css_quantity_plus",
            run: "click",
        },
        {
            content: "One quantity should be added",
            trigger: "input[name=add_qty]:value(2)",
        },
        {
            content: "Try to add one quantity",
            trigger: ".css_quantity_plus",
            run: "click",
        },
        {
            content: "No quantity should be added",
            trigger: "input[name=add_qty]:value(2)",
        },
    ],
});
