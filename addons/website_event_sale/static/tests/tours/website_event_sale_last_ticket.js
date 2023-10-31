odoo.define('website_event_sale.tour.last_ticket', function (require) {
'use strict';

var tour = require('web_tour.tour');

tour.register('event_buy_last_ticket', {
    test: true,
    url: '/event',
},[{
        content: "Open the Last ticket test event page",
        trigger: '.o_wevent_events_list a:contains("Last ticket test")',
    },
    {
        content: "Show available Tickets",
        trigger: '.btn-primary:contains("Register")',
    },
    {
        content: "Select 2 units of `VIP` ticket type",
        extra_trigger: '#wrap:not(:has(a[href*="/event"]:contains("Last ticket test")))',
        trigger: 'select:eq(0)',
        run: 'text 2',
    },
    {
        content: "Click on `Order Now` button",
        extra_trigger: 'select:eq(0):has(option:contains(2):propSelected)',
        trigger: '.a-submit:contains("Register")',
    },
    {
        content: "Fill attendees details",
        trigger: 'form[id="attendee_registration"] .btn:contains("Continue")',
        run: function () {
            $("input[name='1-name']").val("Att1");
            $("input[name='1-phone']").val("111 111");
            $("input[name='1-email']").val("att1@example.com");
            $("input[name='2-name']").val("Att2");
            $("input[name='2-phone']").val("222 222");
            $("input[name='2-email']").val("att2@example.com");
        },
    },
    {
        content: "Validate attendees details",
        extra_trigger: "input[name='1-name'], input[name='2-name']",
        trigger: 'button:contains("Continue")',
    },
    {
        content: "Fill address",
        trigger: 'form.checkout_autoformat',
        run: function () {
            $("input[name='name']").val("test1");
            $("input[name='email']").val("test@example.com");
            $("input[name='phone']").val("111 111");
            $("input[name='street']").val("street test 1");
            $("input[name='city']").val("testCity");
            $("input[name='zip']").val("123");
            $('#country_id option:eq(1)').attr('selected', true);
        },
    },
    {
        content: "Validate address",
        trigger: '.btn-primary:contains("Next")',
    },
    {
        // if the seats_available checking logic is not correct,
        // the shopping cart will be cleared when selling the last ticket
        // the tour test will be failed here
        content: "Select `Wire Transfer` payment method",
        trigger: '#payment_method label:contains("Wire Transfer")',
    },
    // following steps are based on the website_sale_buy.js
    {
        content: "Pay",
        //Either there are multiple payment methods, and one is checked, either there is only one, and therefore there are no radio inputs
        extra_trigger: '#payment_method label:contains("Wire Transfer") input:checked,#payment_method:not(:has("input:radio:visible"))',
        trigger: 'button[name="o_payment_submit_button"]:visible:not(:disabled)',
    },
    {
        content: "payment finish",
        trigger: '.oe_website_sale:contains("Please use the following transfer details")',
        // Leave /shop/confirmation to prevent RPC loop to /shop/payment/get_status.
        // The RPC could be handled in python while the tour is killed (and the session), leading to crashes
        run: function () {
            window.location.href = '/contactus'; // Redirect in JS to avoid the RPC loop (20x1sec)
        },
        timeout: 30000,
    },
    {
        content: "wait page loaded",
        trigger: 'h1:contains("Contact us")',
        run: function () {}, // it's a check
    },
]);
});
