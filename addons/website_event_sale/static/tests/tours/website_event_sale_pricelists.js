odoo.define('website_event_sale.tour.event_sale_pricelists_different_currencies', function (require) {
    'use strict';

    const tour = require('web_tour.tour');
    const { getPriceListChecksSteps } = require('website_event_sale.tour.WebsiteEventSaleTourMethods');

    tour.register('event_sale_pricelists_different_currencies', {
        test: true,
        url: '/event',
    },[
        // Register for tickets
        {
            content: "Open the Pycon event",
            trigger: '.o_wevent_events_list a:contains("Pycon")',
        },
        {
            content: "Register",
            trigger: '.btn-primary:contains("Register")',
        },
        {
            content: "Fill attendees details",
            trigger: 'form[id="attendee_registration"] .btn:contains("Continue")',
            run: function () {
                $("input[name='1-name']").val("Great Name");
                $("input[name='1-phone']").val("111 111");
                $("input[name='1-email']").val("great@name.com");
            },
        },
        {
            content: "Validate attendees details",
            extra_trigger: "input[name='1-name'], input[name='2-name']",
            trigger: 'button:contains("Continue")',
        },
        ...getPriceListChecksSteps({
            pricelistName: "EUR With Discount Included",
            eventName: "Pycon",
            price: "90.00",
        }),
        ...getPriceListChecksSteps({
            pricelistName: "EUR Without Discount Included",
            eventName: "Pycon",
            price: "90.00",
            priceBeforeDiscount: "100.00",
        }),
        ...getPriceListChecksSteps({
            pricelistName: "EX With Discount Included",
            eventName: "Pycon",
            price: "900.00",
        }),
        ...getPriceListChecksSteps({
            pricelistName: "EX Without Discount Included",
            eventName: "Pycon",
            price: "900.00",
            priceBeforeDiscount: "1,000.00",
        }),
    ]);
});
