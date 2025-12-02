import { registry } from "@web/core/registry";
import * as wsTourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('event_buy_last_ticket', {
    url: '/event',
    steps: () => [{
        content: "Open the Last ticket test event page",
        trigger: '.o_wevent_events_list a:contains("Last ticket test")',
        run: "click",
        expectUnloadPage: true,
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
        content: "Edit 2 units of `VIP` ticket type",
        trigger: ".modal input:eq(1)",
        run: "edit 2",
    },
    {
        content: "Click on `Register` button",
        trigger: ".modal .modal-footer button.btn-primary.a-submit:contains(Register)",
        run: "click",
    },
    {
        content: "Check the modal Attendees is opened",
        trigger: ".modal:contains(Attendees):contains(Ticket #1):contains(Ticket #2)",
    },
    {
        content: "Fill attendees details",
        trigger: 'form[id="attendee_registration"] .btn[type=submit]',
        run: function () {
            document.querySelector("input[name*='1-name']").value = "Att1";
            document.querySelector("input[name*='1-phone']").value = "111 111";
            document.querySelector("input[name*='1-email']").value = "att1@example.com";
            document.querySelector("input[name*='2-name']").value = "Att2";
            document.querySelector("input[name*='2-phone']").value = "222 222";
            document.querySelector("input[name*='2-email']").value = "att2@example.com";
        },
    },
    {
        content: "Validate attendees details",
        trigger: ".modal:contains(Attendees) button[type=submit]:contains(Go to Payment)",
        run: "click",
        expectUnloadPage: true,
    },
        ...wsTourUtils.payWithTransfer({
            redirect: true,
            expectUnloadPage: true,
            waitFinalizeYourPayment: true,
        }),
    ],
});
