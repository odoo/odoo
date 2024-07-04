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
            in_modal: false,
            run: "select 1",
        },
        {
            trigger: ".modal select:eq(0):has(option:contains(1):selected)",
            in_modal: false,
        },
        {
            content: "Select 2 units of `VIP` ticket type",
            trigger: ".modal select:eq(1)",
            in_modal: false,
            run: "select 2",
        },
        {
            trigger: ".modal select:eq(1):has(option:contains(2):selected)",
            in_modal: false,
        },
        {
            content: "Click on `Order Now` button",
            trigger: '.modal .btn-primary:contains("Register")',
            in_modal: false,
            run: "click",
        },
        {
            content: "Fill attendees details",
            trigger: 'form[id="attendee_registration"] .btn[type=submit]',
        },
        {
            in_modal: false,
            trigger: ".modal#modal_attendees_registration input[name*='1-email']",
            run: "edit att1@example.com",
        },
        {
            in_modal: false,
            trigger: ".modal#modal_attendees_registration input[name*='1-phone']",
            run: "edit 111 111",
        },
        {
            in_modal: false,
            trigger: ".modal#modal_attendees_registration input[name*='2-name']",
            run: "edit Att2",
        },
        {
            in_modal: false,
            trigger: ".modal#modal_attendees_registration input[name*='2-phone']",
            run: "edit 222 222",
        },
        {
            in_modal: false,
            trigger: ".modal#modal_attendees_registration input[name*='2-email']",
            run: "edit att2@example.com",
        },
        {
            in_modal: false,
            trigger: ".modal#modal_attendees_registration input[name*='1-name']",
            run: "edit Att1",
        },
        {
            in_modal: false,
            trigger: ".modal#modal_attendees_registration input[name*='3-name']",
            run: "edit Att3",
        },
        {
            in_modal: false,
            trigger: ".modal#modal_attendees_registration input[name*='3-phone']",
            run: "edit 333 333",
        },
        {
            in_modal: false,
            trigger: ".modal#modal_attendees_registration input[name*='3-email']",
            run: "edit att3@example.com",
        },
        {
            in_modal: false,
            trigger:
                ".modal#modal_attendees_registration input[name*='1-name'], .modal#modal_attendees_registration input[name*='2-name'], .modal#modal_attendees_registration input[name*='3-name']",
        },
        {
            trigger: "input[name*='1-name'], input[name*='2-name'], input[name*='3-name']",
        },
        {
            in_modal: false,
            content: "Validate attendees details",
            trigger: ".modal#modal_attendees_registration button[type=submit]",
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
