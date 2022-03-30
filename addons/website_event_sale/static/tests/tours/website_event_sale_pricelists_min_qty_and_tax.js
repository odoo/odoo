odoo.define('website_event_sale.tour.event_sale_pricelists_min_quantity_and_tax', function (require) {
    'use strict';

    const { registry } = require("@web/core/registry");
    const { changePricelist, checkPriceCart } = require('website_event_sale.tour.WebsiteEventSaleTourMethods');

    registry.category("web_tour.tours").add('event_sale_pricelists_min_quantity_and_tax', {
        test: true,
        url: '/event',
        steps: [
            ...changePricelist("EUR2 Without Discount Included Min Qty 2"),
            // Register for tickets
            {
                content: "Open the Pycon event",
                trigger: '.o_wevent_events_list a:contains("Pycon")',
            },
            {
                content: "Verify Price",
                trigger: `.oe_currency_value:contains(110.00)`,
                run: function () {}, // it's a check
            },
            {
                content: "Select 2 units",
                extra_trigger: 'select:eq(0):has(option:contains(1):propSelected)',
                trigger: 'select:eq(0)',
                run: 'text 2',
            },
            {
                content: "Verify Price",
                trigger: `.oe_currency_value:contains(99.00)`,
                run: function () {}, // it's a check
            },
            {
                content: "Verify Price before discount",
                trigger: `del:contains(110.00)`,
                run: function () {}, // it's a check
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
                    $("input[name='2-name']").val("Great Name2");
                    $("input[name='2-phone']").val("222 222");
                    $("input[name='2-email']").val("grea2t@name.com");
                },
            },
            {
                content: "Validate attendees details",
                extra_trigger: "input[name='1-name'], input[name='2-name']",
                trigger: 'button:contains("Continue")',
            },
            ...checkPriceCart("198.00")
    ]});
});
