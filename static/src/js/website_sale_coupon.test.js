odoo.define('website_sale_coupon.test', function (require) {
'use strict';

require("website_sale.tour");
var tour = require("web_tour.tour");
var base = require("web_editor.base");
var ajax = require('web.ajax');

tour.register('shop_sale_coupon', {
    test: true,
    url: '/shop',
    wait_for: base.ready()
},
    [
        /* 0. Test 'Show # found' customize option works correctly */
        {
            content: "open customize menu",
            trigger: '#customize-menu > a',
        },
        {
            content: "click on 'Show # found'",
            trigger: "#customize-menu a:contains(Show # found)",
            run: function () {
                if (!$('#customize-menu a:contains(Show # found) input').prop('checked')) {
                    $('#customize-menu a:contains(Show # found)').click();
                }
            },
        },
        /* 1. Buy 1 iPad Mini, enable coupon code & insert 10% code */
        {
            content: "type iPad Mini in search",
            trigger: 'form input[name="search"]',
            run: "text iPad Mini",
        },
        {
            content: "start search",
            trigger: 'form:has(input[name="search"]) .oe_search_button',
        },
        {
            content: "select iPad Mini",
            extra_trigger: '.oe_search_found', // Wait to be on search results or it sometimes throws concurent error (sent search form + click on product on /shop)
            trigger: '.oe_product_cart a:contains("iPad Mini")',
        },
        {
            content: "add 2 iPad Mini into cart",
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
            content: "click on 'Promo Code'",
            trigger: "#customize-menu a:contains(Promo Code)",
            run: function () {
                if (!$('#customize-menu a:contains(Promo Code) input').prop('checked')) {
                    $('#customize-menu a:contains(Promo Code)').click();
                }
            },
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
            trigger: '.reward_product:contains("10.0 % discount on total amount")',
            run: function () {}, // it's a check
        },
        /* 2. Add a product with tax in the cart (which has different tax than iPad) and ensure only one discount line is shown */
        {
            content: "go to shop",
            trigger: '.reward_product:contains("10.0 % discount on total amount")',
            run: function () {
                ajax.jsonRpc('/web/dataset/call', 'call', {
                    model: 'account.tax',
                    method: 'create',
                    args: [{
                      'name':'15% tax incl',
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
            extra_trigger: '.oe_currency_value:contains("-﻿74.00"):not(#cart_total .oe_currency_value:contains("-﻿74.00"))',
            trigger: '.oe_website_sale .oe_cart',
            run: function () {}, // it's a check
        },
        /* 3. Add some iPad to get a free one, play with quantity */
        {
            content: "add one iPad",
            trigger: '#cart_products input.js_quantity',
            run: "text 3",
        },
        {
            content: "check reduction amount got recomputed when changing qty",
            trigger: '.oe_currency_value:contains("-﻿106.00")',
            run: function () {}, // it's a check
        },
        {
            content: "add more iPad Mini into cart",
            trigger: '#cart_products input.js_quantity',
            run: "text 4",
        },
        {
            content: "check free product is added",
            trigger: '#wrap:has(.reward_product:contains("Free Product - iPad Mini"))',
            run: function () {}, // it's a check
        },
        {
            content: "remove one iPad from cart",
            trigger: '#cart_products input.js_quantity[value="4"]',
            run: "text 3",
        },
        {
            content: "check free product is removed",
            trigger: '#wrap:not(:has(.reward_product:contains("Free Product - iPad Mini")))',
            run: function () {}, // it's a check
        },
        /* 4. Check /shop/payment does not break the `merged discount lines split per tax` (eg: with _compute_tax_id) */
        {
            content: "go to checkout",
            trigger: 'a[href="/shop/checkout"]',
        },
        {
            content: "Confirm checkout",
            extra_trigger: "div.all_shipping .panel",
            trigger: 'a[href="/shop/confirm_order"]',
        },
        {
            content: "check total is unchanged",
            trigger: '.oe_currency_value:contains("967.50")',
            run: function () {}, // it's a check
        },
    ]
);

//Check if website_sale_options is installed since its adding an extra step to add to cart
if ('website_sale_options.website_sale' in odoo.__DEBUG__.services) {
  var steps = tour.tours.shop_sale_coupon.steps;
  for (var k=0; k<steps.length; k++) {
      if (steps[k].content === "click on 'Add to Cart' button") {
          steps.splice(k+1, 0, {
              content: "click in modal on 'Proceed to Checkout' button",
              trigger: 'a:contains("Proceed to Checkout")',
          });
      }
  }
}
});
