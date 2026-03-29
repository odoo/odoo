odoo.define('website_sale.website_sale_stock_message_after_close_configurator_modal', function (require) {
    'use strict';

    var tour = require('web_tour.tour');

    // This tour relies on a data created from the python test.
    tour.register('website_sale_stock_message_after_close_onfigurator_modal_with_optional_products', {
        test: true,
        url: '/shop?search=Product With Optional (TEST)',
    },
        [
            {
                content: "Select Customizable Desk",
                trigger: '.oe_product_cart a:contains("Product With Optional (TEST)")',
            }, {
                content: "Check that the stock quantity is displayed and correct",
                trigger: '#threshold_message:contains("30")',
                timout: 1000,
                run: function () { },
            }, {
                content: "Add to cart",
                trigger: '#add_to_cart',
            }, {
                content: "Continue shoppping",
                extra_trigger: '.oe_advanced_configurator_modal',
                trigger: 'button span:contains(Continue Shopping)',
                run: 'click'
            }, {
                content: "Check that the stock quantity is displayed and correct after adding to cart",
                trigger: '#threshold_message:contains("29")',
                timout: 1000,
                run: function () { },
            }
        ]);

    tour.register('website_sale_stock_message_after_close_onfigurator_modal_without_optional_products', {
        test: true,
        url: '/shop?search=Product Without Optional (TEST)',
    },
        [
            {
                content: "Select Office Lamp",
                trigger: '.oe_product_cart a:contains("Product Without Optional (TEST)")',
            }, {
                content: "Check that the stock quantity is displayed and correct",
                trigger: '#threshold_message:contains("30")',
                timout: 1000,
                run: function () { },
            }, {
                content: "Add to cart",
                trigger: '#add_to_cart',
            }, {
                content: "Check that the stock quantity is displayed and correct after adding to cart",
                trigger: '#threshold_message:contains("29")',
                timout: 1000,
                run: function () { },
            }
        ]);
});
