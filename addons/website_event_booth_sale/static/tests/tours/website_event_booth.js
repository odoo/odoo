/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as wsTourUtils from '@website_sale/js/tours/tour_utils';


registry.category("web_tour.tours").add('website_event_booth_tour', {
    url: '/event',
    steps: () => [
{
    content: 'Open "Test Event Booths" event',
    trigger: 'h5.card-title span:contains("Test Event Booths")',
    run: "click",
}, {
    content: 'Go to "Get A Booth" page',
    trigger: 'li.nav-item a:has(span:contains("Get A Booth"))',
    run: "click",
}, {
    content: 'Select the first two booths',
    trigger: ".o_wbooth_booths input[name=event_booth_ids]:not(:visible)",
    run() {
        document.querySelectorAll('.o_wbooth_booths input[name="event_booth_ids"]')[0].click();
        document.querySelectorAll('.o_wbooth_booths input[name="event_booth_ids"]')[1].click();
    },
}, {
    content: 'Confirm the booths by clicking the submit button',
    trigger: 'button.o_wbooth_registration_submit',
    run: "click",
}, {
    content: 'Fill in your contact information',
    trigger: 'input[name="contact_name"]',
    run() {
        this.anchor.value = 'John Doe';
        document.querySelector('input[name="contact_email"]').value = 'jdoe@example.com';
    },
}, {
    content: 'Submit your informations',
    trigger: 'button[type="submit"]',
    run: "click",
},
...wsTourUtils.assertCartAmounts({
    taxes: '20.00',
    untaxed: '200.00',
    total: '220.00',
}),
wsTourUtils.goToCheckout(),
...wsTourUtils.assertCartAmounts({
    taxes: '20.00',
    untaxed: '200.00',
    total: '220.00',
}),
]});
