/** @odoo-module **/

import { registry } from "@web/core/registry";
import wsTourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("event_buy_tickets", {
    test: true,
    url: "/event",
    steps: () => [
        {
            content: "Go to the `Events` page",
            trigger: 'a[href*="/event"]:contains("Conference for Architects TEST"):first',
            run: "click",
        },
        {
            content: "Open the register modal",
            trigger: 'button:contains("Register")',
            run: "click",
        },
        {
            trigger: '#wrap:not(:has(a[href*="/event"]:contains("Conference for Architects")))',
        },
        {
            content: "Select 1 unit of `Standard` ticket type",
            trigger: ".modal select:eq(0)",
            run: "select 1",
        },
        {
            trigger: ".modal select:eq(0):has(option:contains(1):selected)",
        },
        {
            content: "Select 2 units of `VIP` ticket type",
            trigger: ".modal select:eq(1)",
            run: "select 2",
        },
        {
            trigger: ".modal select:eq(1):has(option:contains(2):selected)",
        },
        {
            content: "Click on `Order Now` button",
            trigger: '.modal .btn-primary:contains("Register")',
            run: "click",
        },
        {
            content: "Fill attendees details",
            trigger: 'div[id="attendee_registration_buttons"] .btn[type=submit]',
        },
        {
            trigger: "form[id='attendee_registration'] input[name*='1-email']",
            run: "edit att1@example.com",
        },
        {
            trigger: "form[id='attendee_registration'] input[name*='1-phone']",
            run: "edit 111 111",
        },
        {
            trigger: "form[id='attendee_registration'] input[name*='2-name']",
            run: "edit Att2",
        },
        {
            trigger: "form[id='attendee_registration'] input[name*='2-phone']",
            run: "edit 222 222",
        },
        {
            trigger: "form[id='attendee_registration'] input[name*='2-email']",
            run: "edit att2@example.com",
        },
        {
            trigger: "form[id='attendee_registration'] input[name*='1-name']",
            run: "edit Att1",
        },
        {
            trigger: "form[id='attendee_registration'] input[name*='3-name']",
            run: "edit Att3",
        },
        {
            trigger: "form[id='attendee_registration'] input[name*='3-phone']",
            run: "edit 333 333",
        },
        {
            trigger: "form[id='attendee_registration'] input[name*='3-email']",
            run: "edit att3@example.com",
        },
        {
            trigger:
                "form[id='attendee_registration'] input[name*='1-name'], form[id='attendee_registration'] input[name*='2-name'], form[id='attendee_registration'] input[name*='3-name']",
        },
        {
            trigger: "input[name*='1-name'], input[name*='2-name'], input[name*='3-name']",
        },
        {
            content: "Validate attendees details",
            trigger: "div#attendee_registration_buttons button[type=submit]",
            run: "click",
        },
        wsTourUtils.goToCart({ quantity: 3 }),
        wsTourUtils.goToCheckout(),
        ...wsTourUtils.assertCartAmounts({
            untaxed: "4,000.00",
        }),
        ...wsTourUtils.payWithTransfer(),
    ],
});
