/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('website_event_booth_tour', {
    test: true,
    url: '/event',
}, [
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
}, {
    content: 'Check if the price is correct',
    trigger: 'tr#order_total_untaxed .oe_currency_value:containsExact(200.00)',
    run: function () {},
}, {
    content: 'Check if the tax is correct',
    trigger: 'tr#order_total_taxes .oe_currency_value:containsExact(20.00)',
    run: function () {},
}, {
    content: 'Click confirm to continue',
    trigger: 'a[role="button"] span:contains("Confirm")',
}, {
    content: 'Check if the price is correct',
    trigger: 'tr#order_total_untaxed .oe_currency_value:containsExact(200.00)',
    run: function () {},
}, {
    content: 'Check if the total price is correct',
    trigger: 'tr#order_total .oe_currency_value:containsExact(220.00)',
    run: function () {},
},
]);
