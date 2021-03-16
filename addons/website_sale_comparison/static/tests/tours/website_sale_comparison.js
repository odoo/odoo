odoo.define('website_sale_comparison.tour_comparison', function (require) {
    'use strict';

    var tour = require('web_tour.tour');
    var rpc = require('web.rpc');
    const tourUtils = require('website_sale.tour_utils');

    tour.register('product_comparison', {
        test: true,
        url: "/shop",
    }, [
    // test from shop page
    {
        content: "add first product 'Three-Seat Sofa' in a comparison list",
        trigger: '.oe_product_cart:contains("Three-Seat Sofa") .o_add_compare',
    },
    {
        content: "check compare button contains one product",
        trigger: '.o_product_circle:contains(1)',
        run: function () {},
    },
    {
        content: "check popover is closed when only one product",
        trigger: 'body:not(:has(.comparator-popover))',
        run: function () {},
    },
    {
        content: "add second product 'Conference Chair' in a comparison list",
        trigger: '.oe_product_cart:contains("Conference Chair") .o_add_compare',
    },
    {
        content: "check popover is now open and compare button contains two products",
        extra_trigger: '.comparator-popover',
        trigger: ' .o_product_circle:contains(2)',
        run: function () {},
    },
    {
        content: "check products name are correct in the comparelist",
        extra_trigger: '.o_product_row:contains("Three-Seat Sofa")',
        trigger: '.o_product_row:contains("Conference Chair")',
        run: function () {},
    },
    // test form product page
    {
        content: "go to product page of customizable desk(with variants)",
        trigger: '.oe_product_cart a:contains("Customizable Desk")',
    },
    {
        content: "check compare button is still there and contains 2 products",
        extra_trigger: '#product_details',
        trigger: '.o_product_circle:contains(2)',
        run: function () {},
    },
    {
        content: "check popover is closed after changing page",
        trigger: 'body:not(:has(.comparator-popover))',
        run: function () {},
    },
    {
        content: "add first variant to comparelist",
        trigger: '.o_add_compare_dyn',
    },
    {
        content: "check the comparelist is now open and contains 3rd product with correct variant",
        extra_trigger: '.comparator-popover',
        trigger: '.o_product_row:contains("Customizable Desk (Steel, White)")',
        run: function () {},
    },
    {
        content: "select 2nd variant(Black Color)",
        trigger: '.variant_attribute[data-attribute_name="Color"] input[data-value_name="Black"]',
        run: function (actions) {
          $('img[class*="product_detail_img"]').attr('data-image-to-change', 1);
          actions.click();
        },
    },
    {
        content: "click on compare button to add in comparison list when variant changed",
        extra_trigger: 'img[class*="product_detail_img"]:not([data-image-to-change])',
        trigger: '.o_add_compare_dyn',
    },
    {
        content: "comparelist contains 4th product with correct variant",
        extra_trigger: '.o_product_circle:contains(4)',
        trigger: '.o_product_row:contains("Customizable Desk (Steel, Black)")',
        run: function () {},
    },
    {
        content: "check limit is not reached",
        trigger: ':not(.o_comparelist_limit_warning)',
        run: function () {},
    },
    {
        content: "select 3nd variant(Custom)",
        trigger: '.variant_attribute[data-attribute_name="Legs"] input[data-value_name="Custom"]',
    },
    {
        content: "click on compare button to add in comparison list when variant changed",
        extra_trigger: 'body:not(:has(.carousel-indicators))', // there is 1 image on the custom variant
        trigger: '.o_add_compare_dyn',
    },
    {
        content: "check limit is reached",
        trigger: '.o_comparelist_limit_warning',
        run: function () {},
    },
    {
        content: "click on compare button",
        trigger: '.o_comparelist_button a',
    },
    // test on compare page
    {
        content: "check 1st product contains correct variant",
        trigger: '.o_product_comparison_table:contains("Conference Chair (Steel)")',
        run: function () {},
    },
    {
        content: "check 2nd product contains correct variant",
        trigger: '.o_product_comparison_table:contains("Customizable Desk (Steel, White)")',
        run: function () {},
    },
    {
        content: "check 3rd product is correctly added",
        trigger: '.o_product_comparison_table:contains("Customizable Desk (Steel, Black)")',
        run: function () {},
    },
    {
        content: "check 4th product is correctly added",
        trigger: '.o_product_comparison_table:contains("Three-Seat Sofa")',
        run: function () {},
    },
    {
        content: "remove Customizable Desk (Steel, Black) from compare table",
        trigger: '#o_comparelist_table .o_comparelist_remove:eq(2)',
    },
    {
        content: "check customizable table with black variant is removed",
        trigger: '#o_comparelist_table:not(:contains("Customizable Desk (Steel, Black)"))',
        run: function () {},
    },
    {
        content: "open compare menu",
        extra_trigger: 'body:has(.o_product_row:contains("Three-Seat Sofa") .o_remove)',
        trigger: '.o_product_panel_header',
    },
    {
        content: "remove product",
        trigger: '.o_product_row:contains("Three-Seat Sofa") .o_remove',
    },
    {
        content: "click on compare button to reload",
        trigger: '.o_comparelist_button a',
    },
    {
        content: "check product 'Three-Seat Sofa' is removed",
        trigger: '#o_comparelist_table:not(:contains("Three-Seat Sofa"))',
        run: function () {},
    },
    {
        content: "add product 'Conference Chair' to cart",
        trigger: '.product_summary:contains("Conference Chair") .a-submit:contains("Add to Cart")',
    },
        tourUtils.goToCart(),
    {
        content: "check product correctly added to cart",
        trigger: '#cart_products:contains("Conference Chair") .js_quantity[value="1"]',
        run: function () {},
    },
    // test advanced configuration and alternative product
    {
        content: "create product with newly created attribute and its values and set alternative product",
        trigger: 'body',
        run: function () {
            rpc.query({
                model: 'product.attribute',
                method: 'create',
                args: [{
                    'name': 'color',
                    'display_type': 'color',
                    'create_variant': 'dynamic',
                }],
            }).then(function (attributeId) {
                rpc.query({
                    model: 'product.template',
                    method: 'create',
                    args: [{
                        'name': 'Basic Chair',
                        'is_published': true,
                        'attribute_line_ids': [[0, 0, {
                            'attribute_id': attributeId,
                            'value_ids': [
                                [0, 0, {'name': 'red', 'attribute_id': attributeId, 'sequence': 1}],
                                [0, 0, {'name': 'blue', 'attribute_id': attributeId, 'sequence': 2}],
                            ],
                        }]],
                    }],
                }).then(function (productId) {
                    rpc.query({
                        model: 'product.template',
                        method: 'create',
                        args: [{
                            'name': 'Classic Chair',
                            'is_published': true,
                            'attribute_line_ids': [[0, 0, {
                                'attribute_id': attributeId,
                                'value_ids': [
                                    [0, 0, {'name': 'green', 'attribute_id': attributeId, 'sequence': 3}],
                                    [0, 0, {'name': 'yellow', 'attribute_id': attributeId, 'sequence': 4}],
                                ],
                            }]],
                            'alternative_product_ids': [[6, 0, [productId]]],
                        }],
                    }).then(function () {
                        window.location.href = '/shop?search=Classic Chair';
                    });
                });
            });
        },
    },
    {
        content: "click on product",
        trigger: '.oe_product_cart a:contains("Classic Chair")',
    },
    {
        content: "click on compare button",
        trigger: '.btn.btn-primary:not(.btn-block):contains("Compare")',
    },
    {
        content: "check product 'Classic Chair' with first variant (green) is on compare page",
        trigger: '.o_product_comparison_table:contains("Classic Chair (green)")',
        run: function () {},
    },
    {
        content: "check alternative product 'Basic Chair' with first variant (red) is on compare page",
        trigger: '.o_product_comparison_table:contains("Basic Chair (red)")',
        run: function () {},
    },
    {
        content: "check there is the correct attribute",
        trigger: '.o_ws_category_0:contains("color"):contains("red")',
        run: function () {},
    },
    ]);
});
