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
    },
    {
        content: "add second product 'Large Meeting Table' in a comparison list",
        extra_trigger: '.o_product_circle:not(.o_red_highlight)',
        trigger: '.oe_product_cart:contains("Large Meeting Table") button[data-action=o_comparelist]',
    },
    {
        content: "check popover is now open and compare button contains two products",
        trigger: '.o_product_feature_panel:has(.comparator-popover) .badge:contains(2)',
    },
    {
        content: "check products name are correct in the comparelist",
        trigger: '.comparator-popover .o_comparelist_products:contains("Three-Seat Sofa"):contains("Large Meeting Table")',
    },
    {
        content: "go to product page of customizable desk(with variants)",
        trigger: '.oe_product_cart a:contains("Customizable Desk")',
    },
    {
        content: "check compare button is still there and contains 2 products but it is closed",
        trigger: '.o_product_feature_panel:not(.comparator-popover) .badge:contains(2)',
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
    },
    {
        content: "comparelist contains 4th product with correct variant",
        trigger: '.comparator-popover .o_comparelist_products .o_product_row a:contains("Customizable Desk (Steel, Black)")',
    },
    {
        content: "click on compare button",
        trigger: '.comparator-popover .o_comparelist_button a',
    },
    {
        content: "check 1st product contains correct variant",
        trigger: '.product_summary:eq(0) a:contains("Customizable Desk (Steel, White)")',
    },
    {
        content: "check 2nd product contains correct variant",
        trigger: '.product_summary:eq(1) a:contains("Customizable Desk (Steel, Black)")',
    },
    {
        content: "check 3rd product is correctly added",
        trigger: '.product_summary:eq(2) a:contains("Large Meeting Table")',
    },
    {
        content: "check 4th product is correctly added",
        trigger: '.product_summary:eq(3) a:contains("Three-Seat Sofa")',
    },
    {
        content: "check there are 4 products on compare page",
        trigger: '#o_comparelist_table:contains("Customizable Desk (Steel, White)"):contains("Customizable Desk (Steel, Black)")' +
                ':contains("Large Meeting Table"):contains("Three-Seat Sofa")',
    },
    {
        content: "remove one product from compare table",
        trigger: '#o_comparelist_table',
        run: function () {
            $('#o_comparelist_table td:contains("Customizable Desk (Steel, Black)") a.o_comparelist_remove').click();
            $('body').addClass('notReady');
        }
    },
    {
        content: "check there are 3 products after remove",
        extra_trigger: 'body:not(.notReady)',
        trigger: '#o_comparelist_table:contains("Customizable Desk (Steel, White)")' +
                ':contains("Large Meeting Table"):contains("Three-Seat Sofa")',
    },
    {
        content: "check customizable table with black variant is removed",
        trigger: '#o_comparelist_table td:not(:contains("Customizable Desk (Steel, Black)"))',
    },
    {
        content: "open compare menu",
        trigger: '.o_product_panel_header',
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


    tour.register('product_comparison_dynamic_variant', {
        test: true,
        url: "/",
    }, [
    {
        content: "create product with newly created attribute and its value and set alternative product 'Conference Chair'",
        trigger: '#wrapwrap',
        run: function () {
            rpc.query({
                model: 'product.template',
                method: 'search',
                args: [[['name', '=', "Conference Chair"]]],
            }).then(function (product_id) {
                rpc.query({
                    model: 'product.attribute',
                    method: 'create',
                    args: [{
                        'name': 'color',
                        'type': 'color',
                        'create_variant': 'dynamic'
                    }],
                }).then(function (attribute_id) {
                    rpc.query({
                        model: 'product.template',
                        method: 'create',
                        args: [{
                            'name': 'Bottle',
                            'is_published': true,
                            'attribute_line_ids': [[0, 0 , {
                                'attribute_id': attribute_id,
                                'value_ids': [[0, 0, {
                                        'name': 'red',
                                        'attribute_id': attribute_id,
                                    }],
                                    [0, 0, {
                                        'name': 'blue',
                                        'attribute_id': attribute_id,
                                    }],
                                    [0, 0, {
                                        'name': 'black',
                                        'attribute_id': attribute_id,
                                    }],
                                    ]
                                }]],
                            'alternative_product_ids': [[6, 0, product_id]],
                        }],
                    })
                })
                .then(function () {
                    window.location.href = '/shop';
                });
            })
        },
    },
    {
        content: "search product 'Bottle'",
        extra_trigger: '.js_sale',
        trigger: '#wrapwrap',
        run: function() {
            window.location.href = '/shop?search=Bottle';
        },
    },
    {
        content: "click on product",
        trigger: '.oe_product_cart a:contains("Bottle")',
    },
    {
        content: "click on compare button",
        trigger: '.btn.btn-primary:not(.btn-block):contains("Compare")',
    },
    {
        content: "check product 'Bottle' with first variant(red) is on compare page",
        trigger: '.product_summary:contains("Bottle (red)")',
        run: function () {},
    },
    {
        content: "check there are correct attribute legs",
        trigger: '.General:contains("Legs")',
        run: function () {},
    },
    {
        content: "check there are correct attribute color",
        trigger: '.Uncategorized:contains("color")',
        run: function () {},
    },
    ]);
});
