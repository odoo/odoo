odoo.define('website_sale_comparison.tour_comparison', function (require) {
    "use strict";

    var tour = require('web_tour.tour');
    var rpc = require('web.rpc');

    tour.register('product_comparison', {
        test: true,
        url: "/shop",
    }, [{
        content: "add first product 'Three-seat sofa' in a comparison list",
        trigger: '.oe_product_cart:contains("Three-Seat Sofa") button[data-action=o_comparelist]',
    },
    {
        content: "check popover is closed and compare button contains one product",
        trigger: '.o_product_feature_panel:not(.comparator-popover) .badge:contains(1)',
        run: function () {},
    },
    {
        content: "add second product 'Large Meeting Table' in a comparison list",
        extra_trigger: '.o_product_circle:not(.o_red_highlight)',
        trigger: '.oe_product_cart:contains("Large Meeting Table") button[data-action=o_comparelist]',
    },
    {
        content: "check popover is now open and compare button contains two products",
        trigger: '.o_product_feature_panel:has(.comparator-popover) .badge:contains(2)',
        run: function () {},
    },
    {
        content: "check products name are correct in the comparelist",
        trigger: '.comparator-popover .o_comparelist_products:contains("Three-Seat Sofa"):contains("Large Meeting Table")',
        run: function () {},
    },
    {
        content: "go to product page of customizable desk(with variants)",
        trigger: '.oe_product_cart a:contains("Customizable Desk")',
    },
    {
        content: "check compare button is still there and contains 2 products but it is closed",
        trigger: '.o_product_feature_panel:not(.comparator-popover) .badge:contains(2)',
        run: function () {},
    },
    {
        content: "add product with first variant to comparelist",
        extra_trigger: '#product_details',
        trigger: 'button[data-action=o_comparelist]',
    },
    {
        content: "check the compare is now open",
        trigger: '.o_product_feature_panel .comparator-popover',
        run: function () {},
    },
    {
        content: "check comparelist contains 3rd product with correct variant",
        trigger: '.comparator-popover .o_comparelist_products .o_product_row a:contains("Customizable Desk (Steel, White)")',
        run: function () {},
    },
    {
        content: "select 2nd variant(Black Color)",
        trigger: '.variant_attribute[data-attribute_name="Color"] input[data-value_name="Black"]',
    },
    {
        content:  "click on compare button to add in comparison list",
        extra_trigger: '.o_product_circle:not(.o_red_highlight)',
        trigger: 'button[data-action=o_comparelist]',
    },
    {
        content: "check there are 4 products in comparelist",
        trigger: '#comparelist .badge:contains(4)',
        run: function () {},
    },
    {
        content: "comparelist contains 4th product with correct variant",
        trigger: '.comparator-popover .o_comparelist_products .o_product_row a:contains("Customizable Desk (Steel, Black)")',
        run: function () {},
    },
    {
        content: "click on compare button",
        trigger: '.comparator-popover .o_comparelist_button a',
    },
    {
        content: "check 1st product contains correct variant",
        trigger: '.product_summary:eq(0) a:contains("Customizable Desk (Steel, White)")',
        run: function () {},
    },
    {
        content: "check 2nd product contains correct variant",
        trigger: '.product_summary:eq(1) a:contains("Customizable Desk (Steel, Black)")',
        run: function () {},
    },
    {
        content: "check 3rd product is correctly added",
        trigger: '.product_summary:eq(2) a:contains("Large Meeting Table")',
        run: function () {},
    },
    {
        content: "check 4th product is correctly added",
        trigger: '.product_summary:eq(3) a:contains("Three-Seat Sofa")',
        run: function () {
        },
    },
    {
        content: "check there are 4 products on compare page",
        trigger: '#o_comparelist_table',
        run: function () {
            if ($('#o_comparelist_table thead tr td .o_comparelist_remove').length === 4) {
                console.log("There are 4 products");
                // remove one product from compare page
                $('#o_comparelist_table td:contains("Customizable Desk (Steel, Black)") a strong').click();
                $('body').addClass('notReady');
            }
        }
    },
    {
        content: "check there are 3 products after remove",
        extra_trigger: 'body:not(.notReady)',
        trigger: '#o_comparelist_table',
        run: function () {
            if ($('#o_comparelist_table thead tr td .o_comparelist_remove').length === 3) {
                console.log("There are 3 products after remove");
            }
        }
    },
    {
        content: "check customizable table with black variant is removed",
        trigger: '#o_comparelist_table td:not(:contains("Customizable Desk (Steel, Black)"))',
        run: function () {},
    },
    {
        content: "open compare menu",
        trigger: '.o_product_panel_header',
        run: function (actions) {
            setTimeout(function () {
                actions.click();
            }, 1000);
        }
    },
    {
        content: "remove product",
        trigger: '.comparator-popover .o_comparelist_products .o_product_row:contains("Three-Seat Sofa") .o_remove',
    },
    {
        content: "click on compare button to reload",
        trigger: '.comparator-popover .o_comparelist_button a',
    },
    {
        content: "check product 'Three-Seat Sofa' is removed",
        trigger: '.o_product_comparison_table:not(:contains("Three-Seat Sofa"))',
        run: function () {},
    },
    {
        content: "add product 'Large Meeting Table' to cart",
        trigger: '.product_summary:contains("Customizable Desk (Steel, White)") a:contains("Add to Cart")',
    },
    {
        content: "check product correctly added to cart",
        trigger: '#cart_products:contains("Customizable Desk (Steel, White)") .js_quantity[value="1"]',
    },
    ]);
});
