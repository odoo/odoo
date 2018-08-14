odoo.define('website_sale_coupon.test', function (require) {
'use strict';

require("website_sale.tour");
var tour = require("web_tour.tour");
var base = require("web_editor.base");

tour.register('shop_sale_coupon', {
    test: true,
    url: '/shop?search=Large%20Cabinet',
    wait_for: base.ready()
},
    [
        /* 1. Buy 1 Large Cabinet, enable coupon code & insert 10% code */
        {
            content: "select Large Cabinet",
            trigger: '.oe_product_cart a:contains("Large Cabinet")',
        },
        {
            content: "add 3 Large Cabinet into cart",
            trigger: '#product_details input[name="add_qty"]',
            run: "text 3",
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
        },
        {
            content: "click on 'I have a promo code'",
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
            content: "add more Large Cabinet into cart",
            trigger: '#cart_products input.js_quantity',
            run: "text 4",
        },
        {
            content: "check reduction amount got recomputed",
            extra_trigger: '.oe_currency_value:contains("96.00")', // For some reason, "-96.00" won't work
            trigger: '.reward_product:contains("Free Product - Large Cabinet")',
            run: function () {}, // it's a check
        },
        {
            content: "remove one cabinet from cart",
            trigger: '#cart_products a.js_add_cart_json:first',
        },
        {
            content: "check free product is removed",
            trigger: '#wrap:not(:has(.reward_product:contains("Free Product - Large Cabinet")))',
            run: function () {}, // it's a check
        },
        /* 3. Empty cart and disable coupon */
        {
            content: "remove Large Cabinet from cart",
            trigger: '#cart_products input.js_quantity:first',
            run: "text 0",
        },
        {
            content: "check cart is empty",
            trigger: '#wrap:not(:has(#cart_products))',
            run: function () {}, // it's a check
        },
        /* 4. Disabled customize options coupon box & 'Show # found'*/
        {
            content: "open customize menu",
            extra_trigger: '.oe_website_sale .oe_cart',
            trigger: '#customize-menu > a',
        },
        {
            content: "click on 'Promo Code'",
            trigger: "#customize-menu a:contains(Promo Code)",
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
          break;
      }
  }
}
});
