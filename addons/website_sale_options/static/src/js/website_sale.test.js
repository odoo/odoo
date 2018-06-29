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
            content: "open customize menu",
            trigger: '#customize-menu',
            extra_trigger: "#product_detail",
            run: function() {
                // ENABLE VARIANT GROUP
                $('body').addClass('notReady');
                var ajax = odoo.__DEBUG__.services['web.ajax'];
                var get_group_payload = {
                    model: 'ir.model.data',
                    method: 'xmlid_to_res_id',
                    args: ['product.group_product_variant', false],
                    kwargs: {}
                };
                ajax.jsonpRpc('/web/dataset/call_kw', 'call', get_group_payload).then(function(group_id) {
                    ajax.jsonpRpc('/web/dataset/call_kw', 'call', {
                        model: 'res.groups',
                        method: 'write',
                        args: [group_id, {'users': [[4, 1]]}],
                        kwargs: {}
                    }).then(function() {
                        location.reload(true);
                    });
                });
            },
        },
        {
            content: "open customize menu",
            trigger: '#customize-menu > a',
            extra_trigger: 'body:not(.notReady)',
        },
        {
            content: "check page loaded after enable  variant group",
            trigger: '#customize-menu a:contains(List View of Variants)',
            run: function () {}, // it's a check
        },
        {
            content: "click on 'List View of Variants'",
            trigger: "#customize-menu a:contains(List View of Variants)",
        },
        {
            content: "check page loaded after list of variant customization enabled",
            trigger: '.js_product_change',
            run: function () {}, // it's a check
        },
        {
            content: "check price is 600 and set quantity to 2",
            trigger: ".js_product:first input.quantity:propValue(1)",
            extra_trigger: ".product_price .oe_price .oe_currency_value:containsExact(600.00)",
            run: "text 2",
        },
        {
            content: "verify pricelist based on quantity has effect",
            trigger: ".product_price .oe_price .oe_currency_value:containsExact(450.00)",
            run: function () {}, // it's a check
        },
        {
            content: "check pricelit has been applied and switch to 32 GB variant",
            trigger: ".js_product label:contains('32 GB')",
        },
        {
            content: "verify that price has changed when changing variant",
            trigger: ".product_price .oe_price .oe_currency_value:not(:containsExact(450.00))",
            run: function () {}, // it's a check
        },
        {
            content: "open customize menu",
            trigger: '#customize-menu > a',
        },
        {
            content: "remove 'List View of Variants'",
            trigger: "#customize-menu a:contains(List View of Variants):has(input:checked)",
        },
        {
            content: "check page loaded after list of variant customization disabled",
            trigger: ".js_product:not(:has(.js_product_change))",
            run: function () {}, // it's a check
        },
        {
            content: "check price is 600 and set quantity to 2",
            trigger: ".js_product:first input.quantity:propValue(1)",
            extra_trigger: ".product_price .oe_price .oe_currency_value:containsExact(600.00)",
            run: "text 2",
        },
        {
            content: "verify pricelist based on quantity has effect",
            trigger: ".product_price .oe_price .oe_currency_value:containsExact(450.00)",
            run: function () {}, // it's a check
        },
        {
            content: "switch to 32 GB variant",
            trigger: ".js_product label:contains('32 GB')",
        },
        {
            content: "verify that price has changed when changing variant",
            trigger: ".product_price .oe_price .oe_currency_value:not(:containsExact(450.00))",
            run: function () {}, // it's a check
        },
        {
            content: "switch back to 16 GB variant",
            trigger: ".js_product label:contains('16 GB')",
        },
        {
            content: "click on 'Add to Cart' button",
            trigger: "a:contains(Add to Cart)",
        },
        {
            content: "price is lowered by pricelist and not multiplied by quantity",
            trigger: "#product_confirmation .oe_price .oe_currency_value:containsExact(450.00)",
            extra_trigger: "#product_confirmation input.quantity:propValue(2)",
            run: function () {}, // it's a check
        },
        {
            content: "set quantity to 1",
            trigger: "#product_confirmation .js_add_cart_json .fa-minus",
        },
        {
            content: "check that product page has been updated",
            trigger: ".js_product:first input.quantity:propValue(1)",
            extra_trigger: ".product_price .oe_price .oe_currency_value:containsExact(600.00)",
            run: function () {}, // it's a check
        },
        {
            content: "check that add to cart modal has been updated",
            trigger: "#product_confirmation .oe_price .oe_currency_value:containsExact(600.00)",
            extra_trigger: "#product_confirmation input.quantity:propValue(1)",
            run: function () {}, // it's a check
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
