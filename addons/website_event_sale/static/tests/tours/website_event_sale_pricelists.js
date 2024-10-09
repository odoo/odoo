/** @odoo-module **/

import { registry } from "@web/core/registry";
import { getPriceListChecksSteps } from "@website_event_sale/../tests/tours/helpers/WebsiteEventSaleTourMethods";

registry.category("web_tour.tours").add("event_sale_pricelists_different_currencies", {
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
                '.modal#modal_attendees_registration:not(.o_inactive_modal) form[id="attendee_registration"]',
        },
        {
            trigger:
                ".modal#modal_attendees_registration:not(.o_inactive_modal) input[name*='1-name']",
            run: "edit Great Name",
        },
        {
            trigger:
                ".modal#modal_attendees_registration:not(.o_inactive_modal) input[name*='1-phone']",
            run: "edit 111 111",
        },
        {
            trigger:
                ".modal#modal_attendees_registration:not(.o_inactive_modal) input[name*='1-email']",
            run: "edit great@name.com",
        },
        {
            trigger:
                ".modal#modal_attendees_registration input[name*='1-name'], .modal#modal_attendees_registration input[name*='2-name']",
        },
        {
            trigger: "input[name*='1-name'], input[name*='2-name']",
        },
        {
            content: "Validate attendees details",
            trigger:
                ".modal#modal_attendees_registration:not(.o_inactive_modal) button[type=submit]",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal#modal_attendees_registration))",
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
