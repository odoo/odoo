import { registry } from "@web/core/registry";
import * as wsTourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('website_sale_stock.message_after_close_onfigurator_modal_with_optional_products', {
    // This tour relies on a data created from the python test.
    steps: () => [
        {
            content: "Check that the stock quantity is displayed and correct",
            trigger: '#threshold_message:contains("30")',
        },
        ...wsTourUtils.addToCartFromProductPage(),
        {
            trigger: 'table.o_sale_product_configurator_table',
        },
        {
            content: "Continue shoppping",
            trigger: 'button[name="website_sale_product_configurator_continue_button"]',
            run: 'click',
        },
        {
            content: "Check that the stock quantity is displayed and correct after adding to cart",
            trigger: '#threshold_message:contains("29")',
        },
    ]
});

registry.category("web_tour.tours").add('website_sale_stock.message_after_close_onfigurator_modal_without_optional_products', {
    // This tour relies on a data created from the python test.
    steps: () => [
        {
            content: "Check that the stock quantity is displayed and correct",
            trigger: '#threshold_message:contains("30")',
        },
        ...wsTourUtils.addToCartFromProductPage(),
        {
            content: "Check that the stock quantity is displayed and correct after adding to cart",
            trigger: '#threshold_message:contains("29")',
        },
    ]
});
