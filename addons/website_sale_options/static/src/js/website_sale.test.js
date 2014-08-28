(function () {
    'use strict';
    
    var steps = openerp.Tour.tours.shop_buy_product.steps;
    for (var k=0; k<steps.length; k++) {
        if (steps[k].title === "click on add to cart") {
            steps.splice(k+1, 0, {
                title:     "click in modal on 'Proceed to checkout' button",
                element:   '.modal a:contains("Proceed to checkout")',
            });
            break;
        }
    }

    openerp.Tour.register({
        id:   'shop_customize',
        name: "Customize the page and search a product",
        path: '/shop',
        mode: 'test',
        steps: [
            {
                title:     "open customize menu",
                element:   '#customize-menu-button',
            },
            {
                title:     "click on 'Product Attribute's Filters'",
                element:   "#customize-menu a:contains(Product Attribute's Filters)",
            },
            {
                title:     "select product attribute memory 16 GB",
                waitNot:   '#customize-menu:visible .dropdown-menu:visible',
                element:   'form.js_attributes label:contains(16 GB) input:not(:checked)',
            },
            {
                title:     "check the selection",
                waitFor:   'form.js_attributes label:contains(16 GB) input:checked',
            },
            {
                title:     "select iPad",
                waitNot:   '.oe_website_sale .oe_product_cart:eq(2)',
                element:   '.oe_product_cart a:contains("iPad")',
            },
            {
                title:     "click on 'Add to Cart' button",
                element:   "a:contains(Add to Cart)",
            },
            {
                title:     "add an optional Warranty",
                element:   ".js_product:contains(Warranty) a:contains(Add to Cart)",
            },
            {
                title:     "click in modal on 'Proceed to checkout' button",
                waitFor:   '.js_product:contains(Warranty) a:contains(Add to Cart):hidden',
                element:   '.modal a:contains("Proceed to checkout")',
            },
            {
                title:     "check quantity",
                waitFor:   '.my_cart_quantity:containsExact(2)',
            },
            {
                title:     "check optional product",
                waitFor:   '.optional_product',
            },
            {
                title:     "remove iPad from cart",
                element:   '#cart_products a.js_add_cart_json:first',
            },
            {
                title:     "check optional product is removed",
                waitNot:   '.optional_product',
            },
            {
                title:     "click on shop",
                element:   "a:contains(Shop)",
                waitNot:   '#products_grid_before .js_attributes',
            },
            {
                title:     "open customize menu bis",
                waitFor:   '#products_grid_before .js_attributes',
                element:   '#customize-menu-button',
            },
            {
                title:     "remove 'Product Attribute's Filters'",
                element:   "#customize-menu a:contains(Product Attribute's Filters):has(.fa-check-square-o)",
            },
            {
                title:     "finish",
                waitNot:   '#products_grid_before .js_attributes',
                waitFor:   'li:has(.my_cart_quantity):hidden',
            },
        ]
    });

}());
