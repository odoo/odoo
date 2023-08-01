/** @odoo-module **/

import { registry } from "@web/core/registry";
import wsTourUtils from '@website_sale/js/tours/tour_utils';


registry.category("web_tour.tours").add('website_event_booth_tour', {
    test: true,
    url: '/event',
    steps: () => [
{
    content: 'Open "Test Event Booths" event',
    trigger: 'h5.card-title span:contains("Test Event Booths")',
}, {
    content: 'Go to "Get A Booth" page',
    trigger: 'li.nav-item a:has(span:contains("Get A Booth"))',
}, {
    content: 'Select the first two booths',
    trigger: '.o_wbooth_booths input[name="event_booth_ids"]',
    run: function () {
        $('.o_wbooth_booths input[name="event_booth_ids"]:lt(2)').click();
    },
}, {
    content: 'Confirm the booths by clicking the submit button',
    trigger: 'button.o_wbooth_registration_submit',
}, {
    content: 'Fill in your contact information',
    trigger: 'input[name="contact_name"]',
    run: function () {
        $('input[name="contact_name"]').val('John Doe');
        $('input[name="contact_email"]').val('jdoe@example.com');
    },
}, {
    content: 'Submit your informations',
    trigger: 'button[type="submit"]',
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
