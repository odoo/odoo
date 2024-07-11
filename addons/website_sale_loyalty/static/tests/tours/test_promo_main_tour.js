/** @odoo-module **/

import { jsonrpc } from "@web/core/network/rpc_service";
import { registry } from "@web/core/registry";
import tourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('shop_sale_loyalty', {
    test: true,
    url: '/shop?search=Small%20Cabinet',
    steps: () => [
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
            trigger: "a:contains(Add to cart)",
        },
            tourUtils.goToCart({quantity: 2}),
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
            trigger: 'div>strong:contains("10.0% discount on total amount")',
            run: function () {}, // it's a check
        },
        {
            content: "check loyalty points",
            trigger: '.oe_website_sale_gift_card span:contains("372.03 Points")',
            run: function () {}, // it's a check
        },
        /* 2. Add some cabinet to get a free one, play with quantity */
        {
            content: "go to shop",
            trigger: 'div>strong:contains("10.0% discount on total amount")',
            run: function () {
                jsonrpc('/web/dataset/call_kw/account.tax/create', {
                    model: 'account.tax',
                    method: 'create',
                    args: [{
                      'name':'15% tax incl ' + new Date().getTime(),
                      'amount': 15,
                    }],
                    kwargs: {},
                }).then(function (tax_id) {
                    jsonrpc('/web/dataset/call_kw/product.template/create', {
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
            ...tourUtils.addToCart({productName: "Taxed Product"}),
            tourUtils.goToCart({quantity: 3}),
        {
            content: "check reduction amount got recomputed and merged both discount lines into one only",
            extra_trigger: '.oe_currency_value:contains("-﻿74.00"):not(#cart_total .oe_currency_value:contains("-﻿74.00"))',
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
            trigger: '.oe_currency_value:contains("-﻿106.00")',
            run: function () {}, // it's a check
        },
        {
            content: "add more Small Cabinet into cart",
            trigger: '#cart_products input.js_quantity',
            run: "text 4",
        },
        {
            content: "check free product is added",
            trigger: '#wrap:has(div>strong:contains("Free Product - Small Cabinet"))',
            run: function () {}, // it's a check
        },
        {
            content: "remove one cabinet from cart",
            trigger: '#cart_products input.js_quantity[value="4"]',
            run: "text 3",
        },
        {
            content: "check free product is removed",
            trigger: '#wrap:not(:has(div>strong:contains("Free Product - Small Cabinet")))',
            run: function () {}, // it's a check
        },
        /* 4. Check /shop/payment does not break the `merged discount lines split per tax` (eg: with _compute_tax_id) */
        {
            content: "go to checkout",
            trigger: 'a[href="/shop/checkout?express=1"]',
        },
        ...tourUtils.assertCartAmounts({
            total: '967.50',
        }),
    ]
});
