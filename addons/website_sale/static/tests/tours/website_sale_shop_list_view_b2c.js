odoo.define('website_sale.tour_shop_list_view_b2c', function (require) {
'use strict';

var rpc = require('web.rpc');
var tour = require('web_tour.tour');

tour.register('shop_list_view_b2c', {
    test: true,
    url: '/shop?search=Test Product',
},
    [
        {
            content: "activate b2c",
            trigger: 'body',
            run: function () {
                return rpc.query({
                    model: 'res.config.settings',
                    method: 'create',
                    args: [{
                        'auth_signup_uninvited': 'b2c',
                        'show_line_subtotals_tax_selection': 'tax_included',
                        'group_show_line_subtotals_tax_excluded': false,
                        'group_show_line_subtotals_tax_included': true,
                    }],
                }).then(function (resId) {
                    return rpc.query({
                        model: 'res.config.settings',
                        method: 'execute',
                        args: [[resId]],
                    }).then(function () {
                        window.location.reload();
                    });
                });
            },
        },
        {
            content: "check price on /shop",
            trigger: '.oe_product_cart .oe_currency_value:contains("825.00")',
            run: function () {},
        },
        {
            content: "select product",
            trigger: '.oe_product_cart a:contains("Test Product")',
        },
        {
            content: "check list view of variants is disabled initially (when on /product page)",
            trigger: 'body:not(:has(.js_product_change))',
            extra_trigger: '#product_details',
            run: function () {},
        },
        {
            content: "open customize menu",
            trigger: '#customize-menu > a',
            extra_trigger: 'body:not(.notReady)',
        },
        {
            content: "click on 'List View of Variants'",
            trigger: '#customize-menu a:contains(List View of Variants)',
        },
        {
            content: "check page loaded after list of variant customization enabled",
            trigger: '.js_product_change',
            run: function () {},
        },
        {
            context: "check variant price",
            trigger: '.custom-radio:contains("Aluminium") .badge:contains("+") .oe_currency_value:contains("55.44")',
            run: function () {},
        },
        {
            content: "check price is 825",
            trigger: '.product_price .oe_price .oe_currency_value:containsExact("825.00")',
            run: function () {},
        },
        {
            content: "switch to another variant",
            trigger: '.js_product label:contains("Aluminium")',
        },
        {
            content: "verify that price has changed when changing variant",
            trigger: '.product_price .oe_price .oe_currency_value:containsExact("880.44")',
            run: function () {},
        },
        {
            content: "click on 'Add to Cart' button",
            trigger: 'a:contains(Add to Cart)',
        },
        {
            content: "check price on /cart",
            trigger: '#cart_products .oe_currency_value:containsExact("880.44")',
            run: function () {},
        },
    ]
);

});
