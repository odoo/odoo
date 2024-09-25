/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as wsTourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("event_buy_last_ticket", {
    test: true,
    url: "/event",
    checkDelay: 100,
    steps: () => [
        {
            content: "Open the Last ticket test event page",
            trigger: '.o_wevent_events_list a:contains("Last ticket test")',
            run: "click",
        },
        {
            content: "Open Registration Modal",
            trigger: ".btn-primary:contains(Register)",
            run: "click",
        },
        {
            content: "Check the modal Tickets is opened",
            trigger: "body:has(.modal:contains(Tickets))",
        },
        {
            trigger: '#wrap:not(:has(a[href*="/event"]:contains("Last ticket test")))',
        },
        {
            content: "Select 2 units of `VIP` ticket type",
            trigger: ".modal select:eq(0)",
            run: "select 2",
        },
        {
            trigger: ".modal select:eq(0):has(option:contains(2):selected)",
        },
        {
            content: "Click on `Order Now` button",
            trigger: ".modal .modal-footer button.btn-primary.a-submit:contains(Register)",
            run: "click",
        },
        {
            content: "Check the modal Attendees is opened",
            trigger: "body:has(.modal:contains(Attendees):contains(Ticket #1):contains(Ticket #2))",
        },
        {
            content: "Fill name of attendee 1",
            trigger: ".modal input[name*='1-name']",
            run: "edit Att1",
        },
        {
            content: "Fill phone of attendee 1",
            trigger: ".modal input[name*='1-phone']",
            run: "edit 111-111",
        },
        {
            content: "Fill email of attendee 1",
            trigger: ".modal input[name*='1-email']",
            run: "edit att1@example.com",
        },
        {
            content: "Fill name of attendee 2",
            trigger: ".modal input[name*='2-name']",
            run: "edit Att2",
        },
        {
            content: "Fill phone of attendee 2",
            trigger: ".modal input[name*='2-phone']",
            run: "edit 222-222",
        },
        {
            content: "Fill email of attendee 2",
            trigger: ".modal input[name*='2-email']",
            run: "edit att2@example.com",
        },
        {
            content: "Validate attendees details",
            trigger: ".modal button[type=submit]:contains(Go to Payment)",
            run: "click",
        },
        ...wsTourUtils.fillAdressForm({
            name: "test1",
            phone: "111 111",
            email: "test@example.com",
            street: "street test 1",
            city: "testCity",
            zip: "123",
        }),
        ...wsTourUtils.payWithTransfer(true),
    ],
});
