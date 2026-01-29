/** @odoo-module **/

import { registry } from "@web/core/registry";
import wsTourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('event_buy_tickets', {
    test: true,
    url: '/event',
    steps: () => [
        {
            content: "Go to the `Events` page",
            trigger: 'a[href*="/event"]:contains("Conference for Architects TEST"):first',
        }, 
        {
            content: "Open the register modal",
            trigger: 'button:contains("Register")',
        },
        {
            content: "Select 1 unit of `Standard` ticket type",
            extra_trigger: '#wrap:not(:has(a[href*="/event"]:contains("Conference for Architects")))',
            trigger: 'select:eq(0)',
            run: 'text 1',
        },
        {
            content: "Select 2 units of `VIP` ticket type",
            extra_trigger: 'select:eq(0):has(option:contains(1):propSelected)',
            trigger: 'select:eq(1)',
            run: 'text 2',
        },
        {
            content: "Click on `Order Now` button",
            extra_trigger: 'select:eq(1):has(option:contains(2):propSelected)',
            trigger: '.btn-primary:contains("Register")',
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
                $("input[name*='3-name']").val("Att3");
                $("input[name*='3-phone']").val("333 333");
                $("input[name*='3-email']").val("att3@example.com");
            },
        },
        {
            content: "Validate attendees details",
            extra_trigger: "input[name*='1-name'], input[name*='2-name'], input[name*='3-name']",
            trigger: 'button[type=submit]',
        },
        wsTourUtils.goToCart({quantity: 3}),
        wsTourUtils.goToCheckout(),
        ...wsTourUtils.assertCartAmounts({
            untaxed: '4,000.00',
        }),
        ...wsTourUtils.payWithTransfer(),
    ]
});
