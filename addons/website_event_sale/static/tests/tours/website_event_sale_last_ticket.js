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
        run: 'text 2',
    },
    {
        content: "Click on `Order Now` button",
        extra_trigger: 'select:eq(0):has(option:contains(2):propSelected)',
        trigger: '.a-submit:contains("Register")',
    },
    {
        content: "Fill attendees details",
        trigger: 'form[id="attendee_registration"] .btn[type=submit]',
        run: function () {
            $("input[name*='1-name']").val("Att1");
            $("input[name*='1-phone']").val("111 111");
            $("input[name*='1-email']").val("att1@example.com");
            $("input[name*='2-name']").val("Att2");
            $("input[name*='2-phone']").val("222 222");
            $("input[name*='2-email']").val("att2@example.com");
        },
    },
    {
        content: "Validate attendees details",
        extra_trigger: "input[name*='1-name'], input[name*='2-name']",
        trigger: 'button[type=submit]',
    },
    {
        content: "Fill address",
        trigger: 'form.checkout_autoformat',
        run: function () {
            $("input[name='name']").val("test1");
            $("input[name='email']").val("test@example.com");
            $("input[name='phone']").val("111 111");
            $("input[name='street']").val("street test 1");
            $("input[name='city']").val("testCity");
            $("input[name='zip']").val("123");
            $('#country_id option:eq(1)').attr('selected', true);
        },
    },
    {
        content: "Validate address",
        trigger: '.btn-primary:contains("Continue checkout")',
    },
    ...wsTourUtils.payWithTransfer(true),
]});
