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
                element:   'form.js_attributes label:contains(16 Go) input:not(:checked)',
            },
            {
                title:     "check the selection",
                waitFor:   'form.js_attributes label:contains(16 Go) input:checked',
            },
            {
                title:     "select ipod",
                waitNot:   '.oe_website_sale .oe_product_cart:eq(2)',
                element:   '.oe_product_cart a:contains("iPod")',
            },
            {
                title:     "finish",
                waitFor:   'form[action="/shop/cart/update"] label:contains(32 Go) input',
            }
        ]
    });

    openerp.Tour.register({
        id:   'shop_buy_product',
        name: "Try to buy products",
        path: '/shop',
        mode: 'test',
        steps: [
            {
                title:     "select ipod",
                element:   '.oe_product_cart a:contains("iPod")',
            },
            {
                title:     "select ipod 32Go",
                waitFor:   '#product_detail',
                element:   'label:contains(32 Go) input',
            },
            {
                title:     "click on add to cart",
                waitFor:   'label:contains(32 Go) input[checked]',
                element:   'form[action="/shop/cart/update"] .btn',
            },
            {
                title:     "add suggested",
                waitNot:   '#cart_products:contains("[A8767] Apple In-Ear Headphones")',
                element:   'form[action="/shop/cart/update"] .btn-link:contains("Add to Cart")',
            },
            {
                title:     "add one more iPod",
                waitFor:   '.my_cart_quantity:contains(2)',
                element:   '#cart_products tr:contains("32 Go") a.js_add_cart_json:eq(1)',
            },
            {
                title:     "remove Headphones",
                waitFor:   '#cart_products tr:contains("32 Go") input.js_quantity[value=2]',
                element:   '#cart_products tr:contains("Apple In-Ear Headphones") a.js_add_cart_json:first',
            },
            {
                title:     "set one iPod",
                waitNot:   '#cart_products tr:contains("Apple In-Ear Headphones")',
                element:   '#cart_products input.js_quantity',
                sampleText: '1',
            },
            {
                title:     "go to checkout",
                waitFor:   '#cart_products input.js_quantity[value=1]',
                element:   'a[href="/shop/checkout"]',
            },
            {
                title:     "test with input error",
                element:   'form[action="/shop/confirm_order"] .btn:contains("Confirm")',
                onload: function (tour) {
                    $("input[name='phone']").val("");
                },
            },
            {
                title:     "test without input error",
                waitFor:   'form[action="/shop/confirm_order"] .has-error',
                element:   'form[action="/shop/confirm_order"] .btn:contains("Confirm")',
                onload: function (tour) {
                    if ($("input[name='name']").val() === "")
                        $("input[name='name']").val("website_sale-test-shoptest");
                    if ($("input[name='email']").val() === "")
                        $("input[name='email']").val("website_sale_test_shoptest@websitesaletest.optenerp.com");
                    $("input[name='phone']").val("123");
                    $("input[name='street']").val("123");
                    $("input[name='city']").val("123");
                    $("input[name='zip']").val("123");
                    $("select[name='country_id']").val("21");
                },
            },
            {
                title:     "select payment",
                element:   '#payment_method label:has(img[title="Wire Transfer"]) input',
            },
            {
                title:     "Pay Now",
                waitFor:   '#payment_method label:has(input:checked):has(img[title="Wire Transfer"])',
                element:   '.oe_sale_acquirer_button .btn[type="submit"]:visible',
            },
            {
                title:     "finish",
                waitFor:   '.oe_website_sale:contains("Thank you for your order")',
            }
        ]
    });

}());
