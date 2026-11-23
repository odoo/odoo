/** @odoo-module **/

    import { registry } from "@web/core/registry";
    import { getPriceListChecksSteps } from "@website_event_sale/../tests/tours/helpers/WebsiteEventSaleTourMethods";

    registry.category("web_tour.tours").add('event_sale_pricelists_different_currencies', {
        test: true,
        url: '/event',
        steps: () => [
        // Register for tickets
        {
            content: "Open the Pycon event",
            trigger: '.o_wevent_events_list a:contains("Pycon")',
        },
        {
            content: "Open the register modal",
            trigger: 'button:contains("Register")',
        },
        {
            content: "Click on Register button inside modal",
            trigger: 'div.modal-footer button:contains("Register")',
            run: 'click'
        },
        {
            content: "Fill attendees details",
            trigger: 'form[id="attendee_registration"]',
            run: function () {
                $("input[name*='1-name']").val("Great Name");
                $("input[name*='1-phone']").val("111 111");
                $("input[name*='1-email']").val("great@name.com");
            },
        },
        {
            content: "Validate attendees details",
            extra_trigger: "input[name*='1-name'], input[name*='2-name']",
            trigger: 'button[type=submit]',
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
    ]});
