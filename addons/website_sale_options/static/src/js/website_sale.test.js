odoo.define('website_sale.test', function (require) {
'use strict';

require("website_sale.tour");
var tour = require("web_tour.tour");
var base = require("web_editor.base");

var steps = tour.tours.shop_buy_product.steps;
for (var k=0; k<steps.length; k++) {
    if (steps[k].content === "click on add to cart") {
        steps.splice(k+1, 0, {
            content: "click in modal on 'Proceed to checkout' button",
            trigger: 'a:contains("Proceed to Checkout")',
        });
        break;
    }
}

tour.register('shop_customize', {
    test: true,
    url: '/shop',
    wait_for: base.ready()
},
    [
        {
            content: "open customize menu",
            trigger: '#customize-menu > a',
        },
        {
            content: "click on 'Product Attribute's Filters'",
            trigger: "#customize-menu a:contains(Product Attribute's Filters)",
        },
        {
            content: "select product attribute memory 16 GB",
            extra_trigger: 'body:not(:has(#customize-menu:visible .dropdown-menu:visible))',
            trigger: 'form.js_attributes label:contains(16 GB) input:not(:checked)',
        },
        {
            content: "check the selection",
            trigger: 'form.js_attributes label:contains(16 GB) input:checked',
            run: function () {}, // it's a check
        },
        {
            content: "select iPad",
            extra_trigger: 'body:not(:has(.oe_website_sale .oe_product_cart:eq(2)))',
            trigger: '.oe_product_cart a:contains("iPad")',
        },
        {
            content: "click on 'Add to Cart' button",
            trigger: "a:contains(Add to Cart)",
        },
        {
            content: "add an optional Warranty",
            trigger: ".js_product:contains(Warranty) a:contains(Add to Cart)",
        },
        {
            content: "click in modal on 'Proceed to checkout' button",
            extra_trigger: 'body:has(.js_product:contains(Warranty) a:contains(Add to Cart):hidden)',
            trigger: '.modal-dialog a:contains("Proceed to Checkout")',
        },
        {
            content: "check quantity",
            trigger: '.my_cart_quantity:containsExact(2)',
            run: function () {}, // it's a check
        },
        {
            content: "check optional product",
            trigger: '.optional_product',
            run: function () {}, // it's a check
        },
        {
            content: "remove iPad from cart",
            trigger: '#cart_products a.js_add_cart_json:first',
        },
        {
            content: "check optional product is removed",
            trigger: '#wrap:not(:has(.optional_product))',
            run: function () {}, // it's a check
        },
        {
            content: "click on shop",
            trigger: "a:contains(Continue Shopping)",
            extra_trigger: 'body:not(:has(#products_grid_before .js_attributes))',
        },
        {
            content: "open customize menu bis",
            extra_trigger: '#products_grid_before .js_attributes',
            trigger: '#customize-menu > a',
        },
        {
            content: "remove 'Product Attribute's Filters'",
            trigger: "#customize-menu a:contains(Product Attribute's Filters):has(input:checked)",
        },
        {
            content: "finish",
            extra_trigger: 'body:not(:has(#products_grid_before .js_attributes))',
            trigger: '#wrap:not(:has(li:has(.my_cart_quantity):visible))',
            run: function () {}, // it's a check
        },
    ]
);

});
