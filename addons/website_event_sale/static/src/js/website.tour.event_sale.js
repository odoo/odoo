(function () {
    'use strict';

    openerp.Tour.register({
        id:   'event_buy_tickets',
        name: "Try to buy tickets for event",
        path: '/event',
        mode: 'test',
        steps: [
            {
                title:     "select event",
                element:   'a[href*="/event"]:contains("Conference on Business Applications"):first',
            },
            {
                waitNot:   'a[href*="/event"]:contains("Conference on Business Applications")',
                title:     "select 2 Standard tickets",
                element:   'select:eq(0)',
                sampleText: '2',
            },
            {
                title:     "select 3 VIP tickets",
                waitFor:   'select:eq(0) option:contains(2):selected',
                element:   'select:eq(1)',
                sampleText: '3',
            },
            {
                title:     "Order Now",
                waitFor:   'select:eq(1) option:contains(3):selected',
                element:   '.btn-primary:contains("Order Now")',
            },
            {
                title:     "Check the cart",
                element:   'a:has(.my_cart_quantity):contains(5)'
            },
            {
                title:     "Check if the cart have 2 order lines and add one VIP ticket",
                waitFor:   "#cart_products:contains(Standard):contains(VIP)",
                element:   "#cart_products tr:contains(VIP) .fa-plus",
            },
            {
                title:     "Process Checkout",
                waitFor:   'a:has(.my_cart_quantity):contains(6)',
                element:   '.btn-primary:contains("Process Checkout")'
            },
            {
                title:     "Complete checkout",
                element:   'form[action="/shop/confirm_order"] .btn:contains("Confirm")',
                autoComplete: function (tour) {
                    if ($("input[name='name']").val() === "")
                        $("input[name='name']").val("website_sale-test-shoptest");
                    if ($("input[name='email']").val() === "")
                        $("input[name='email']").val("website_event_sale_test_shoptest@websiteeventsaletest.odoo.com");
                    $("input[name='phone']").val("123");
                    $("input[name='street2']").val("123");
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
