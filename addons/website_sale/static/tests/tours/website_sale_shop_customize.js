odoo.define('website_sale.tour_shop_customize', function (require) {
    'use strict';

    var tour = require("web_tour.tour");
    const tourUtils = require('website_sale.tour_utils');

    tour.register('shop_customize', {
        test: true,
        url: '/shop',
    },
        [
            {
                content: "open customize menu",
                trigger: '#customize-menu > a',
            },
            {
                content: "click on 'Attributes & Variants filters'",
                trigger: "#customize-menu label:contains(Attributes & Variants filters)",
            },
            {
                content: "select product attribute Steel",
                extra_trigger: 'body:not(:has(#customize-menu:visible .dropdown-menu:visible))',
                trigger: 'form.js_attributes input:not(:checked) + label:contains(Steel - Test)',
            },
            {
                content: "check the selection",
                trigger: 'form.js_attributes input:checked + label:contains(Steel - Test)',
                run: function () {}, // it's a check
            },
            {
                content: "select product",
                extra_trigger: 'body:not(:has(.oe_website_sale .oe_product_cart:eq(3)))',
                trigger: '.oe_product_cart a:contains("Test Product")',
            },
            {
                content: "open customize menu",
                trigger: '#customize-menu > a',
                extra_trigger: '#product_detail',
            },
            {
                content: "check page loaded after enable  variant group",
                trigger: '#customize-menu label:contains(List View of Variants)',
                run: function () {}, // it's a check
            },
            {
                content: "check list view of variants is disabled initially",
                trigger: 'body:not(:has(.js_product_change))',
                run: function () {},
            },
            {
                content: "click on 'List View of Variants'",
                trigger: "#customize-menu label:contains(List View of Variants)",
            },
            {
                content: "check page loaded after list of variant customization enabled",
                trigger: '.js_product_change',
                run: function () {}, // it's a check
            },
            {
                context: "check variant price",
                trigger: '.custom-radio:contains("Aluminium") .badge:contains("+") .oe_currency_value:contains("50.4")',
                run: function () {},
            },
            {
                content: "check price is 750",
                trigger: ".product_price .oe_price .oe_currency_value:containsExact(750.00)",
                run: function () {},
            },
            {
                content: "switch to another variant",
                trigger: ".js_product label:contains('Aluminium')",
            },
            {
                content: "verify that price has changed when changing variant",
                trigger: ".product_price .oe_price .oe_currency_value:containsExact(800.40)",
                run: function () {},
            },
            {
                content: "open customize menu",
                trigger: '#customize-menu > a',
            },
            {
                content: "remove 'List View of Variants'",
                trigger: "#customize-menu label:contains(List View of Variants):has(input:checked)",
            },
            {
                content: "check page loaded after list of variant customization disabled",
                trigger: ".js_product:not(:has(.js_product_change))",
                run: function () {}, // it's a check
            },
            {
                content: "check price is 750",
                trigger: ".product_price .oe_price .oe_currency_value:containsExact(750.00)",
                run: function () {},
            },
            {
                content: "switch to Aluminium variant",
                trigger: '.js_product input[data-value_name="Aluminium"]',
            },
            {
                content: "verify that price has changed when changing variant",
                trigger: ".product_price .oe_price .oe_currency_value:containsExact(800.40)",
                run: function () {}, // it's a check
            },
            {
                content: "switch back to Steel variant",
                trigger: ".js_product label:contains('Steel - Test')",
            },
            {
                content: "check price is 750",
                trigger: ".product_price .oe_price .oe_currency_value:containsExact(750.00)",
                run: function () {},
            },
            {
                content: "click on 'Add to Cart' button",
                trigger: "a:contains(ADD TO CART)",
            },
            {
                content: "check quantity",
                trigger: '.my_cart_quantity:containsExact(1),.o_extra_menu_items .fa-plus',
                run: function () {}, // it's a check
            },
                tourUtils.goToCart(),
            {
                content: "click on shop",
                trigger: "a:contains(Continue Shopping)",
                extra_trigger: 'body:not(:has(#products_grid_before .js_attributes))',
            },
            {
                content: "open customize menu bis",
                extra_trigger: '#products_grid_before .js_attributes',
                trigger: '#customize-menu > a',
            },
            {
                content: "remove 'Attributes & Variants filters'",
                trigger: "#customize-menu label:contains(Attributes & Variants filters):has(input:checked)",
            },
            {
                content: "finish",
                extra_trigger: 'body:not(:has(#products_grid_before .js_attributes))',
                trigger: '#wrap:not(:has(li:has(.my_cart_quantity):visible))',
                run: function () {}, // it's a check
            },
        ]
    );

    });
