odoo.define('website_sale_wishlist_admin.tour', function (require) {
'use strict';

var rpc = require('web.rpc');
var tour = require("web_tour.tour");

tour.register('shop_wishlist_admin', {
    test: false,
    url: '/shop',
},
    [
        {
            content: "Create a product with always attribute and its values.",
            trigger: 'body',
            run: function () {
                rpc.query({
                    model: 'product.attribute',
                    method: 'create',
                    args: [{
                        'name': "color",
                        'display_type': 'color',
                        'create_variant': 'always'
                    }],
                }).then(function (attributeId) {
                    return rpc.query({
                        model: 'product.template',
                        method: 'create',
                        args: [{
                            'name': "Rock",
                            'is_published': true,
                            'attribute_line_ids': [[0, 0, {
                                'attribute_id': attributeId,
                                'value_ids': [
                                    [0, 0, {
                                        'name': "red",
                                        'attribute_id': attributeId,
                                    }],
                                    [0, 0, {
                                        'name': "blue",
                                        'attribute_id': attributeId,
                                    }],
                                    [0, 0, {
                                        'name': "black",
                                        'attribute_id': attributeId,
                                    }],
                                ]
                            }]],
                        }],
                    });
                }).then(function () {
                    window.location.href = '/shop?search=Rock';
                });
            },
        },
        {
            content: "Go to Rock shop page",
            trigger: 'a:contains("Rock"):first',
        },
        {
            content: "check list view of variants is disabled initially (when on /product page)",
            trigger: 'body:not(:has(.js_product_change))',
            extra_trigger: '#product_details',
        },
        {
            content: "open customize menu",
            trigger: '#customize-menu > a',
            extra_trigger: 'body:not(.notReady)',
        },
        {
            content: "click on 'List View of Variants'",
            trigger: '#customize-menu label:contains(List View of Variants)',
        },
        {
            content: "check page loaded after list of variant customization enabled",
            trigger: '.js_product_change',
        },
        {
            content: "Add red product in wishlist",
            trigger: '#product_detail .o_add_wishlist_dyn:not(".disabled")',
        },
        {
            content: "Check that wishlist contains 1 items",
            extra_trigger : '#product_detail .o_add_wishlist_dyn:disabled',
            trigger: '.my_wish_quantity:contains(1)',
            run: function () {
                window.location.href = '/shop/wishlist';
            }
        },
        {
            content: "Check wishlist contains first variant",
            trigger: '#o_comparelist_table tr:contains("red")',
            run: function () {
                window.location.href = '/shop?search=Rock';
            }
        },
        {
            content: "Go to Rock shop page",
            trigger: 'a:contains("Rock"):first',
        },
        {
            content: "Switch to black Rock",
            trigger: '.js_product span:contains("black")',
        },
        {
            content: "Switch to black Rock",
            trigger: '#product_detail .o_add_wishlist_dyn:not(".disabled")',
        },
        {
            content: "Check that black product was added",
            extra_trigger : '#product_detail .o_add_wishlist_dyn:disabled',
            trigger: '.my_wish_quantity:contains(2)',
            run: function () {
                window.location.href = '/shop/wishlist';
            }
        },
        {
            content: "Check wishlist contains both variants",
            extra_trigger: '#o_comparelist_table tr:contains("red")',
            trigger: '#o_comparelist_table tr:contains("black")',
        },
    ]
);

});
