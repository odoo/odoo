(function () {
    'use strict';

    var website = openerp.website;

    website.Tour.register({
        id:   'event_buy_tickets',
        name: "Try to buy tickets for event",
        path: '/event',
        mode: 'test',
        steps: [
            {
                title:     "select event",
                element:   'a[href*="/event"]:contains("Open Days in Los Angeles"):first',
            },
            {
                title:     "go to register page",
                waitNot:   'a[href*="/event"]:contains("Functional Webinar")',
                autoComplete:   function () {
                    // use onload if website_event_track is installed
                    if (!$('form:contains("Ticket Type")').size()) {
                        window.location.href = $('a[href*="/event/Open-Days-in-Los-Angeles"][href*="/register"]').attr("href");
                    }
                },
            },
            {
                title:     "select 2 Standard tickets",
                element:   'select[name="ticket-1"]',
                sampleText: '2',
            },
            {
                title:     "select 3 VIP tickets",
                waitFor:   'select[name="ticket-1"] option:contains(2):selected',
                element:   'select[name="ticket-2"]',
                sampleText: '3',
            },
            {
                title:     "Order Now",
                waitFor:   'select[name="ticket-2"] option:contains(3):selected',
                element:   '.btn-primary:contains("Order Now")',
            },
            {
                title:     "Complete checkout",
                waitFor:   '#top_menu .my_cart_quantity:contains(5)',
                element:   'form[action="/shop/confirm_order"] .btn:contains("Confirm")',
                autoComplete: function (tour) {
                    if ($("input[name='name']").val() === "")
                        $("input[name='name']").val("website_sale-test-shoptest");
                    if ($("input[name='email']").val() === "")
                        $("input[name='email']").val("website_event_sale_test_shoptest@websiteeventsaletest.optenerp.com");
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
                element:   '.oe_sale_acquirer_button .btn[name="submit"]:visible',
            },
            {
                title:     "finish",
                waitFor:   '.oe_website_sale:contains("Thank you for your order")',
            }
        ]
    });

}());
