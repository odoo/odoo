import { registry } from "@web/core/registry";
import * as wsTourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("event_buy_tickets", {
    url: "/event",
    steps: () => [
        {
            content: "Go to the `Events` page",
            trigger: 'a[href*="/event"]:contains("Conference for Architects TEST"):first',
            run: "click",
            expectUnloadPage: true,
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
            content: "Try reaching maximum `Standard` ticket orderable",
            trigger: ".modal input:eq(1)",
            run: "edit 1234",
        },
        {
            // The input number should be changed to EVENT_MAX_TICKETS without particular conditions (EVENT_MAX_TICKETS < 1234)
            trigger: "div.o_wevent_ticket_selector:contains('Max.') input.form-control",
        },
        {
            content: "Reset to 0",
            trigger: ".modal input:eq(1)",
            run: "edit 0"
        },
        {
            content: "Add 1 unit of `Standard` ticket type thanks to the spinner",
            trigger: "button[data-increment-type*='plus']",
            run: "click",
        },
        {
            content: "Try reaching maximum `VIP` ticket orderable",
            trigger: ".modal input:eq(2)",
            run: "edit 2002",
        },
        {
            // The input number should be changed to min(limit per order, seats available) (11 < 12 < 2002)
            trigger: "div.o_wevent_ticket_selector:contains('VIP'):contains('11') input.form-control",
        },
        {
            content: "Edit 2 units of `VIP` ticket type",
            trigger: ".modal input:eq(2)",
            run: "edit 2",
        },
        {
            content: "Click on `Order Now` button",
            trigger: '.modal .btn-primary:contains("Register")',
            run: "click",
        },
        {
            content: "Wait the modal is shown before continue",
            trigger: ".modal.modal_shown.show form[id=attendee_registration]",
        },
        {
            trigger: ".modal#modal_attendees_registration input[name*='1-email']",
            run: "edit att1@example.com",
        },
        {
            trigger: ".modal#modal_attendees_registration input[name*='1-phone']",
            run: "edit 111 111",
        },
        {
            trigger: ".modal#modal_attendees_registration input[name*='2-name']",
            run: "edit Att2",
        },
        {
            trigger: ".modal#modal_attendees_registration input[name*='2-phone']",
            run: "edit 222 222",
        },
        {
            trigger: ".modal#modal_attendees_registration input[name*='2-email']",
            run: "edit att2@example.com",
        },
        {
            trigger: ".modal#modal_attendees_registration input[name*='1-name']",
            run: "edit Att1",
        },
        {
            trigger: ".modal#modal_attendees_registration input[name*='3-name']",
            run: "edit Att3",
        },
        {
            trigger: ".modal#modal_attendees_registration input[name*='3-phone']",
            run: "edit 333 333",
        },
        {
            trigger: ".modal#modal_attendees_registration input[name*='3-email']",
            run: "edit att3@example.com",
        },
        {
            trigger:
                ".modal#modal_attendees_registration input[name*='1-name'], .modal#modal_attendees_registration input[name*='2-name'], .modal#modal_attendees_registration input[name*='3-name']",
        },
        {
            trigger: "input[name*='1-name'], input[name*='2-name'], input[name*='3-name']",
        },
        {
            content: "Validate attendees details",
            trigger: ".modal#modal_attendees_registration button[type=submit]",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: ".oe_cart:contains(payment method)",
        },
        wsTourUtils.goToCart({ quantity: 3 }),
        wsTourUtils.goToCheckout(),
        ...wsTourUtils.assertCartAmounts({
            untaxed: "4,000.00",
        }),
        ...wsTourUtils.payWithTransfer({ expectUnloadPage: true, waitFinalizeYourPayment: true }),
    ],
});
