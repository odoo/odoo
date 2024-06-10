/** @odoo-module **/

import { registry } from "@web/core/registry";
import { getPriceListChecksSteps } from "@website_event_sale/../tests/tours/helpers/WebsiteEventSaleTourMethods";

registry.category("web_tour.tours").add("event_sale_pricelists_different_currencies", {
    test: true,
    url: "/event",
    steps: () => [
        // Register for tickets
        {
            content: "Open the Pycon event",
            trigger: '.o_wevent_events_list a:contains("Pycon")',
            run: "click",
        },
        {
            content: "Open the register modal",
            trigger: 'button:contains("Register")',
            run: "click",
        },
        {
            content: "Click on Register button inside modal",
            trigger: '.modal .modal-footer button:contains("Register")',
            run: "click",
        },
        {
            trigger:
                'form[id="attendee_registration"]',
        },
        {
            trigger:
                "form[id='attendee_registration'] input[name*='1-name']",
            run: "edit Great Name",
        },
        {
            trigger:
                "form[id='attendee_registration'] input[name*='1-phone']",
            run: "edit 111 111",
        },
        {
            trigger:
                "form[id='attendee_registration'] input[name*='1-email']",
            run: "edit great@name.com",
        },
        {
            trigger:
                "form[id='attendee_registration'] input[name*='1-name'], form[id='attendee_registration'] input[name*='2-name']",
        },
        {
            trigger: "input[name*='1-name'], input[name*='2-name']",
        },
        {
            content: "Validate attendees details",
            trigger:
                "div#attendee_registration_buttons button[type=submit].btn-primary",
            run: "click",
        },
        {
            trigger: "body:not(:has(form[id='attendee_registration']))",
        },
        ...getPriceListChecksSteps({
            pricelistName: "EUR Without Discount Included",
            eventName: "Pycon",
            price: "90.00",
            priceBeforeDiscount: "100.00",
        }),
        ...getPriceListChecksSteps({
            pricelistName: "EX Without Discount Included",
            eventName: "Pycon",
            price: "900.00",
            priceBeforeDiscount: "1,000.00",
        }),
    ],
});
