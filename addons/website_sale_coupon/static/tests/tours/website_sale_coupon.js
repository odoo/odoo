odoo.define('website_sale_coupon.test', function (require) {
'use strict';

require("website_sale.tour");
var tour = require("web_tour.tour");
var ajax = require('web.ajax');

tour.register('shop_sale_coupon', {
    test: true,
    url: '/shop?search=Large%20Cabinet',
},
    [
        {
            content: "open customize menu",
            extra_trigger: '.oe_website_sale .o_wsale_products_searchbar_form',
            trigger: '#customize-menu > a',
        },
        {
            content: "enable 'Show # found' if needed",
            trigger: "#customize-menu a:contains(Show # found)",
            run: function () {
                if (!$('#customize-menu a:contains(Show # found) input').prop('checked')) {
                    $('#customize-menu a:contains(Show # found)').click();
                }
            }
        },
        /* 1. Buy 1 Large Cabinet, enable coupon code & insert 10% code */
        {
            content: "select Large Cabinet",
            extra_trigger: '.oe_search_found',
            trigger: '.oe_product_cart a:contains("Large Cabinet")',
        },
        {
            content: "add 2 Large Cabinet into cart",
            trigger: '#product_details input[name="add_qty"]',
            run: "text 2",
        },
        {
            content: "click on 'Add to Cart' button",
            trigger: "a:contains(Add to Cart)",
        },
        {
            content: "open customize menu",
            extra_trigger: '.oe_website_sale .oe_cart',
            trigger: '#customize-menu > a',
        },
        {
            content: "enable 'Promo Code' if needed",
            trigger: "#customize-menu a:contains(Promo Code)",
            run: function () {
                if (!$('#customize-menu a:contains(Promo Code) input').prop('checked')) {
                    $('#customize-menu a:contains(Promo Code)').click();
                }
            }
        },
        {
            content: "click on 'I have a promo code'",
            extra_trigger: '.show_coupon',
            trigger: '.show_coupon',
        },
        {
            content: "insert promo code '10pc'",
            extra_trigger: 'form[name="coupon_code"]',
            trigger: 'form[name="coupon_code"] input[name="promo"]',
            run: "text 10pc",
        },
        {
            content: "validate the coupon",
            trigger: 'form[name="coupon_code"] .a-submit',
        },
        {
            content: "check reward product",
            trigger: '.reward_product:contains("10.0% discount on total amount")',
            run: function () {}, // it's a check
        },
        /* 2. Add some cabinet to get a free one, play with quantity */
        {
            content: "go to shop",
            trigger: '.reward_product:contains("10.0% discount on total amount")',
            run: function () {
                ajax.jsonRpc('/web/dataset/call', 'call', {
                    model: 'account.tax',
                    method: 'create',
                    args: [{
                      'name':'15% tax incl ' + _.now(),
                      'amount': 15,
                    }],
                }).then(function (tax_id) {
                    ajax.jsonRpc('/web/dataset/call', 'call', {
                        model: 'product.template',
                        method: 'create',
                        args: [{
                          'name': 'Taxed Product',
                          'taxes_id': [([6, false, [tax_id]])],
                          'list_price': 100,
                          'website_published': true,
                        }],
                    }).then(function (data) {
                        location.href = '/shop';
                    });
                });
            },
        },
        {
            content: "type Taxed Product in search",
            trigger: 'form input[name="search"]',
            run: "text Taxed Product",
        },
        {
            content: "start search",
            trigger: 'form:has(input[name="search"]) .oe_search_button',
        },
        {
            content: "select Taxed Product",
            extra_trigger: '.oe_search_found', // Wait to be on search results or it sometimes throws concurent error (sent search form + click on product on /shop)
            trigger: '.oe_product_cart a:containsExact("Taxed Product")',
        },
        {
            content: "click on 'Add to Cart' button",
            trigger: "a:contains(Add to Cart)",
        },
        {
            content: "check reduction amount got recomputed and merged both discount lines into one only",
            extra_trigger: '.oe_currency_value:contains("-﻿75.50"):not(#cart_total .oe_currency_value:contains("-﻿75.50"))',
            trigger: '.oe_website_sale .oe_cart',
            run: function () {}, // it's a check
        },
        /* 3. Add some cabinet to get a free one, play with quantity */
        {
            content: "add one Large Cabinet",
            trigger: '#cart_products input.js_quantity',
            run: "text 3",
        },
        {
            content: "check reduction amount got recomputed when changing qty",
            trigger: '.oe_currency_value:contains("-﻿107.50")',
            run: function () {}, // it's a check
        },
        {
            content: "add more Large Cabinet into cart",
            trigger: '#cart_products input.js_quantity',
            run: "text 4",
        },
        {
            content: "check free product is added",
            trigger: '#wrap:has(.reward_product:contains("Free Product - Large Cabinet"))',
            run: function () {}, // it's a check
        },
        {
            content: "remove one cabinet from cart",
            trigger: '#cart_products input.js_quantity[value="4"]',
            run: "text 3",
        },
        {
            content: "check free product is removed",
            trigger: '#wrap:not(:has(.reward_product:contains("Free Product - Large Cabinet")))',
            run: function () {}, // it's a check
        },
        /* 4. Check /shop/payment does not break the `merged discount lines split per tax` (eg: with _compute_tax_id) */
        {
            content: "go to checkout",
            trigger: 'a[href="/shop/checkout?express=1"]',
        },
        {
            content: "check total is unchanged",
            trigger: 'tr#order_total .oe_currency_value:contains("967.50")',
            run: function () {}, // it's a check
        },
    ]
);
});
