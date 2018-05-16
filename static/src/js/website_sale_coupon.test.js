odoo.define('website_sale_coupon.test', function (require) {
'use strict';

require("website_sale.tour");
var tour = require("web_tour.tour");
var base = require("web_editor.base");

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
            content: "click on 'Coupon Code'",
            trigger: "#customize-menu a:contains(Coupon Code)",
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
        /* 2. Add an Ice Cream in the cart (which has different tax than iPad) and ensure only one discount line is shown */
        {
            content: "go to shop",
            trigger: '.reward_product:contains("10.0 % discount on total amount")',
            run: function () {
                location.href = '/shop'
            },
        },
        {
            content: "type Ice Cream in search",
            trigger: 'form input[name="search"]',
            run: "text Ice Cream",
        },
        {
            content: "start search",
            trigger: 'form:has(input[name="search"]) .oe_search_button',
        },
        {
            content: "select Ice Cream",
            extra_trigger: '.oe_search_found', // Wait to be on search results or it sometimes throws concurent error (sent search form + click on product on /shop)
            trigger: '.oe_product_cart a:containsExact("Ice Cream")',
        },
        {
            content: "click on 'Add to Cart' button",
            trigger: "a:contains(Add to Cart)",
        },
        {
            content: "check reduction amount got recomputed and merged both discount lines into one only",
            extra_trigger: '.oe_currency_value:contains("‑74.00")',
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
            trigger: '.oe_currency_value:contains("‑106.00")',
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
        /* 4. Empty cart and disable coupon */
        {
            content: "remove iPad Mini from cart",
            trigger: '#cart_products input.js_quantity[value="3"]',
            run: "text 0",
        },
        {
            content: "remove Ice Cream from cart",
            extra_trigger: '#wrap:not(:has(.td-product_name:contains("iPad Mini")))', // wait iPad got removed
            trigger: '#cart_products input.js_quantity[value="1"]',
            run: "text 0",
        },
        {
            content: "check cart is empty",
            trigger: '#wrap:not(:has(#cart_products))',
            run: function () {}, // it's a check
        },
        /* 5. Disabled customize options coupon box & 'Show # found'*/
        {
            content: "open customize menu",
            extra_trigger: '.oe_website_sale .oe_cart',
            trigger: '#customize-menu > a',
        },
        {
            content: "click on 'Coupon Code'",
            trigger: "#customize-menu a:contains(Coupon Code)",
        },
        {
            content: "click on 'Continue Shopping'",
            trigger: "a:contains(Continue Shopping)",
        },
        {
            content: "open customize menu",
            extra_trigger: '.oe_website_sale #products_grid',
            trigger: '#customize-menu > a',
        },
        {
            content: "click on 'Show # found'",
            trigger: "#customize-menu a:contains(Show # found)",
        },
    ]
);

//Check if website_sale_options is installed since its adding an extra step to add to cart
if ('website_sale_options.website_sale' in odoo.__DEBUG__.services) {
  var steps = tour.tours.shop_sale_coupon.steps;
  for (var k=0; k<steps.length; k++) {
      if (steps[k].content === "click on 'Add to Cart' button") {
          steps.splice(k+1, 0, {
              content: "click in modal on 'Proceed to checkout' button",
              trigger: 'a:contains("Proceed to checkout")',
          });
      }
  }
}
});
