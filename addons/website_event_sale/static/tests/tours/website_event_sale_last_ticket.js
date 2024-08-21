/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as wsTourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('event_buy_last_ticket', {
    test: true,
    url: '/event',
    steps: () => [{
        content: "Open the Last ticket test event page",
        trigger: '.o_wevent_events_list a:contains("Last ticket test")',
        run: "click",
    },
    {
        content: "Open Registration Page",
        trigger: '.btn-primary:contains("Register")',
        run: "click",
    },
    {
        content: "Open the register modal",
        trigger: 'button:contains("Register")',
        run: "click",
    },
    {
        trigger: '#wrap:not(:has(a[href*="/event"]:contains("Last ticket test")))',
    },
    {
        content: "Select 2 units of `VIP` ticket type",
        trigger: 'select:eq(0)',
        run: "select 2",
    },
    {
        trigger: "select:eq(0):has(option:contains(2):selected)",
    },
    {
        content: "Click on `Order Now` button",
        trigger: '.a-submit:contains("Register")',
        run: "click",
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
        trigger: "input[name*='1-name'], input[name*='2-name']",
    },
    {
        content: "Validate attendees details",
        trigger: "button[type=submit]:contains(Go to Payment)",
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
]});
