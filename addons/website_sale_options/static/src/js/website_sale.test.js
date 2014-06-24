(function () {
    'use strict';
    
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
                title:     "select product attribute memory 16 Go",
                waitNot:   '#customize-menu:visible',
                element:   'form.js_attributes label:contains(16 Go) input:not(:checked)',
            },
            {
                title:     "check the selection",
                waitFor:   'form.js_attributes label:contains(16 Go) input:checked',
            },
            {
                title:     "select iPod",
                waitNot:   '.oe_website_sale .oe_product_cart:eq(2)',
                element:   '.oe_product_cart a:contains("iPod")',
            },
            {
                title:     "open customize menu 2",
                waitFor:   'form[action^="/shop/cart/update"] label:contains(32 Go) input',
                element:   '#customize-menu-button',
            },
            {
                title:     "click on 'Confirm: Add To Cart'",
                element:   "#customize-menu a:contains(Confirm: Add To Cart)",
            },
            {
                title:     "click on 'Add to Cart' button",
                waitNot:   '#customize-menu:visible',
                element:   "a[data-toggle='modal']:contains(Add to Cart)",
            },
            {
                title:     "click in modal on 'Proceed to checkout' button",
                element:   '.modal a:contains("Proceed to checkout")',
            },
            {
                title:     "return to the iPod product",
                waitFor:   '#cart_products',
                element:   "a:contains(iPod)",
            },
            {
                title:     "open customize menu 3",
                waitFor:   'form[action^="/shop/cart/update"] label:contains(32 Go) input',
                element:   '#customize-menu-button',
            },
            {
                title:     "click on 'Confirm: Add To Cart'",
                element:   "#customize-menu a:contains(Confirm: Add To Cart)",
            },
            {
                title:     "click on 'My Cart'",
                waitFor:   "a.a-submit:contains(Add to Cart)",
                element:   "a[href='/shop/cart']",
            },
            {
                title:     "remove iPod from cart",
                element:   '#cart_products a.js_add_cart_json:first',
            },
            {
                title:     "finish",
                waitFor:   '.my_cart_quantity:contains(1)',
            },
        ]
    });

}());
