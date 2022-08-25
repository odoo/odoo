/** @odoo-module **/

import tour from 'web_tour.tour';
import ajax from 'web.ajax';
import tourUtils from 'website_sale.tour_utils';

tour.register('shop_sale_loyalty', {
    test: true,
    url: '/shop?search=Small%20Cabinet',
},
    [
        /* 1. Buy 1 Small Cabinet, enable coupon code & insert 10% code */
        {
            content: "select Small Cabinet",
            extra_trigger: '.oe_search_found',
            trigger: '.oe_product_cart a:contains("Small Cabinet")',
        },
        {
            content: "add 2 Small Cabinet into cart",
            trigger: '#product_details input[name="add_qty"]',
            run: "text 2",
        },
        {
            content: "click on 'Add to Cart' button",
            trigger: "a:contains(ADD TO CART)",
        },
            tourUtils.goToCart({quantity: 2}),
        {
            content: "click on 'I have a promo code'",
            extra_trigger: '.show_coupon',
            trigger: '.show_coupon',
        },
        {
            content: "insert promo code 'testcode'",
            extra_trigger: 'form[name="coupon_code"]',
            trigger: 'form[name="coupon_code"] input[name="promo"]',
            run: "text testcode",
        },
        {
            content: "validate the coupon",
            trigger: 'form[name="coupon_code"] .a-submit',
        },
        {
            content: "check reward product",
            trigger: '.td-product_name:contains("10.0% discount on total amount")',
            run: function () {}, // it's a check
        },
        /* 2. Add some cabinet to get a free one, play with quantity */
        {
            content: "go to shop",
            trigger: '.td-product_name:contains("10.0% discount on total amount")',
            run: function () {
                ajax.jsonRpc('/web/dataset/call_kw', 'call', {
                    model: 'account.tax',
                    method: 'create',
                    args: [{
                      'name':'15% tax incl ' + _.now(),
                      'amount': 15,
                    }],
                    kwargs: {},
                }).then(function (tax_id) {
                    ajax.jsonRpc('/web/dataset/call_kw', 'call', {
                        model: 'product.template',
                        method: 'create',
                        args: [{
                          'name': 'Taxed Product',
                          'taxes_id': [([6, false, [tax_id]])],
                          'list_price': 100,
                          'website_published': true,
                        }],
                        kwargs: {},
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
            trigger: "a:contains(ADD TO CART)",
        },
            tourUtils.goToCart({quantity: 3}),
        {
            content: "check reduction amount got recomputed and merged both discount lines into one only",
            extra_trigger: '.oe_currency_value:contains("-﻿75.50"):not(#cart_total .oe_currency_value:contains("-﻿75.50"))',
            trigger: '.oe_website_sale .oe_cart',
            run: function () {}, // it's a check
        },
        /* 3. Add some cabinet to get a free one, play with quantity */
        {
            content: "add one Small Cabinet",
            trigger: '#cart_products input.js_quantity',
            run: "text 3",
        },
        {
            content: "check reduction amount got recomputed when changing qty",
            trigger: '.oe_currency_value:contains("-﻿107.50")',
            run: function () {}, // it's a check
        },
        {
            content: "add more Small Cabinet into cart",
            trigger: '#cart_products input.js_quantity',
            run: "text 4",
        },
        {
            content: "check free product is added",
            trigger: '#wrap:has(.td-product_name:contains("Free Product - Small Cabinet"))',
            run: function () {}, // it's a check
        },
        {
            content: "remove one cabinet from cart",
            trigger: '#cart_products input.js_quantity[value="4"]',
            run: "text 3",
        },
        {
            content: "check free product is removed",
            trigger: '#wrap:not(:has(.td-product_name:contains("Free Product - Small Cabinet")))',
            run: function () {}, // it's a check
        },
        /* 4. Check /shop/payment does not break the `merged discount lines split per tax` (eg: with _compute_tax_id) */
        {
            content: "go to checkout",
            trigger: 'a[href="/shop/checkout?express=1"]',
        },
        {
            content: "check total is unchanged once we land on payment page",
            extra_trigger: '#payment_method h3:contains("Pay with")',
            trigger: 'tr#order_total .oe_currency_value:contains("967.50")',
            run: function () {}, // it's a check
        },
    ]
);
