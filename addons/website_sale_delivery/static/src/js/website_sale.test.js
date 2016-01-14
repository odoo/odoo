(function () {
    'use strict';

    openerp.Tour.register({
        id:   'shop_buy_delivery',
        name: "Customize the page and search a product",
        path: '/shop',
        mode: 'test',
        steps: [
            {
                title:     'step 0 select ipod',
                element:   '.oe_product_cart a:contains("iPod")',
            },
            {
                title:     'step 1 select ipod 32GB',
                waitFor:   '#product_detail',
                element:   'label:contains(32 GB) input',
            },
            {
                title:     'step 2 click on add to cart on ipod details',
                waitFor:   'label:contains(32 GB) input[checked]',
                element:   'form[action^="/shop/cart/update"] .btn',
            },
            {
                title:     'step 3 search an ipad in order to have two products',
                element:   'form:has(input[name="search"]):first .btn',
                onload: function() {
                    $('input[name="search"]').val("ipad");
                }
            },
            {
                title:     'step 4 go in the ipad information',
                element:   '.oe_product_cart a:contains("iPad Mini")',
            },
            {
                title:     "step 5 add to chart from the full view for ipad",
                element:   'form[action^="/shop/cart/update"] .btn',
            },
            {
                title:     "click in modal on 'Proceed to checkout' button",
                element:   '.modal a:contains("Proceed to checkout")',
            },
            {
                title:     "step 6 go to checkout",
                element:   'a:contains("Process Checkout")',
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
                        $("input[name='email']").val("website_sale_test_shoptest@websitesaletest.odoo.com");
                    $("input[name='phone']").val("123");
                    $("input[name='street2']").val("123");
                    $("input[name='city']").val("123");
                    $("input[name='zip']").val("123");
                    $("select[name='country_id']").val("21");
                },
            },
            {
                title:     "select a delivery method",
                element:   'label:contains("Free delivery charges") input',
                onload: function (tour) {
                    $('label:contains("Free delivery charges") input').on( "click", function() {
                        $('label:contains("Free delivery charges") input').prop('checked', true);
                    });
                    $('label:contains("Free delivery charges") input').trigger( "click" );
                }
            },
            {
                title:     "select payment",
                element:   '#payment_method label:has(img[title="Wire Transfer"]) input',
            },
            {
                title:     "Pay Now",
                element:   '.oe_sale_acquirer_button .btn[type="submit"]:visible',
                onload: function (tour) {
                    $('#payment_method label:has(img[title="Wire Transfer"]) input').on( "click", function() {
                        $('#payment_method label:has(img[title="Wire Transfer"]) input').prop('checked', true);
                    });
                    $('#payment_method label:has(img[title="Wire Transfer"]) input').trigger( "click" );
                }
            },
            {
                title:     "finish",
                waitFor:   '.oe_website_sale:contains("Thank you for your order")',
            }
        ]
    });

}());
