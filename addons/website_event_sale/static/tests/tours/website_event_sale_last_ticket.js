/** @odoo-module **/

import { registry } from "@web/core/registry";
import wsTourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('event_buy_last_ticket', {
    test: true,
    url: '/event',
    steps: () => [{
        content: "Open the Last ticket test event page",
        trigger: '.o_wevent_events_list a:contains("Last ticket test")',
    },
    {
        content: "Open Registration Page",
        trigger: '.btn-primary:contains("Register")',
    },
    {
        content: "Open the register modal",
        trigger: 'button:contains("Register")',
    },
    {
        content: "Select 2 units of `VIP` ticket type",
        extra_trigger: '#wrap:not(:has(a[href*="/event"]:contains("Last ticket test")))',
        trigger: 'select:eq(0)',
        run: "select 2",
    },
    {
        content: "Click on `Order Now` button",
        extra_trigger: 'select:eq(0):has(option:contains(2):selected)',
        trigger: '.a-submit:contains("Register")',
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
        extra_trigger: "input[name*='1-name'], input[name*='2-name']",
        trigger: "button[type=submit]:contains(Go to Payment)",
    },
    {
        content: "Fill address",
        trigger: 'form.checkout_autoformat',
        run: function () {
            document.querySelector("input[name='name']").value = "test1";
            document.querySelector("input[name='email']").value = "test@example.com";
            document.querySelector("input[name='phone']").value = "111 111";
            document.querySelector("input[name='street']").value = "street test 1";
            document.querySelector("input[name='city']").value = "testCity";
            document.querySelector("input[name='zip']").value = "123";
            document.querySelectorAll("#country_id option")[1].selected = true;
        },
    },
    {
        content: "Validate address",
        trigger: 'a.a-submit.btn-primary',
    },
    ...wsTourUtils.payWithTransfer(true),
]});
