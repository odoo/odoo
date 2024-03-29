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
            run: "select 1",
        },
        {
            content: "Select 2 units of `VIP` ticket type",
            extra_trigger: 'select:eq(0):has(option:contains(1):selected)',
            trigger: 'select:eq(1)',
            run: "select 2",
        },
        {
            content: "Click on `Order Now` button",
            extra_trigger: 'select:eq(1):has(option:contains(2):selected)',
            trigger: '.btn-primary:contains("Register")',
        },
        {
            content: "Fill attendees details",
            trigger: 'form[id="attendee_registration"] .btn[type=submit]',
            run: function () {
                document.querySelector("input[name*='1-email']").value = "att1@example.com";
                document.querySelector("input[name*='1-phone']").value = "111 111";
                document.querySelector("input[name*='2-name']").value = "Att2";
                document.querySelector("input[name*='2-phone']").value = "222 222";
                document.querySelector("input[name*='2-email']").value = "att2@example.com";
                document.querySelector("input[name*='1-name']").value = "Att1";
                document.querySelector("input[name*='3-name']").value = "Att3";
                document.querySelector("input[name*='3-phone']").value = "333 333";
                document.querySelector("input[name*='3-email']").value = "att3@example.com";
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
