odoo.define('survey.tour_test_certification_failure', function (require) {
'use strict';

/**
 * This tour will test that, for the demo certification allowing 2 attempts, a user can
 * try and fail twice and will no longer be able to take the certification.
 */

var tour = require('web_tour.tour');

var failSteps = [{ // Page-1
    content: "Clicking on Start Certification",
    trigger: 'a.btn.btn-primary.btn-lg:contains("Start Certification")',
}, { // Question: Do we sell Acoustic Bloc Screens?
    content: "Selecting answer 'No'",
    trigger: 'div.js_question-wrapper:contains("Do we sell Acoustic Bloc Screens") select',
    run: 'text No',
}, { // Question: Select all the existing products
    content: "Ticking answer 'Fanta'",
    trigger: 'div.js_question-wrapper:contains("Select all the existing products") label:contains("Fanta") input'
}, {
    content: "Ticking answer 'Drawer'",
    trigger: 'div.js_question-wrapper:contains("Select all the existing products") label:contains("Drawer") input'
}, {
    content: "Ticking answer 'Conference chair'",
    trigger: 'div.js_question-wrapper:contains("Select all the existing products") label:contains("Conference chair") input'
}, { // Question: Select all the available customizations for our Customizable Desk
    content: "Ticking answer 'Color'",
    trigger: 'div.js_question-wrapper:contains("Select all the available customizations for our Customizable Desk") label:contains("Color") input'
}, {
    content: "Ticking answer 'Height'",
    trigger: 'div.js_question-wrapper:contains("Select all the available customizations for our Customizable Desk") label:contains("Height") input'
}, { // Question: How many versions of the Corner Desk do we have?
    content: "Selecting answer '2'",
    trigger: 'div.js_question-wrapper:contains("How many versions of the Corner Desk do we have") select',
    run: 'text 2',
}, { // Question: Do you think we have missing products in our catalog? (not rated)
    content: "Missing products",
    trigger: 'div.js_question-wrapper:contains("Do you think we have missing products in our catalog") textarea',
    run: "text I don't know products enough to be able to answer that",
}, { // Page-2 Question: How much do we sell our Cable Management Box?
    content: "Selecting answer '80$'",
    trigger: 'div.js_question-wrapper:contains("How much do we sell our Cable Management Box") select',
    run: function () {
        var $select = $('div.js_question-wrapper:contains("How much do we sell our Cable Management Box") select');
        $select.val($('option:contains("80$")').val());
    }
}, { // Question: Select all the the products that sell for 100$ or more
    content: "Ticking answer 'Corner Desk Right Sit'",
    trigger: 'div.js_question-wrapper:contains("Select all the the products that sell for 100$ or more") label:contains("Corner Desk Right Sit") input'
}, {
    content: "Ticking answer 'Desk Combination'",
    trigger: 'div.js_question-wrapper:contains("Select all the the products that sell for 100$ or more") label:contains("Desk Combination") input'
}, {
    content: "Ticking answer 'Office Chair Black'",
    trigger: 'div.js_question-wrapper:contains("Select all the the products that sell for 100$ or more") label:contains("Office Chair Black") input'
}, { // Question: What do you think about our prices (not rated)?
    trigger: 'div.js_question-wrapper:contains("What do you think about our prices") select',
    run: function () {
        var $select = $('div.js_question-wrapper:contains("What do you think about our prices") select');
        $select.val($('option:contains("Correctly priced")').val());
    }
}, {
    content: "Finish Survey",
    trigger: 'button[value="finish"]',
}];

var retrySteps = [{
    trigger: 'a:contains("Retry")'
}];

var lastSteps = [{
    trigger: 'h1:contains("Thank you!")',
    run: function () {
        if ($('a:contains("Retry")').length === 0) {
            $('h1:contains("Thank you!")').addClass('tour_success');
        }
    }
}, {
    trigger: 'h1.tour_success',
}];

tour.register('test_certification_failure', {
    test: true,
    url: '/survey/start/4ead4bc8-b8f2-4760-a682-1fde8ddb95ac'
}, [].concat(failSteps, retrySteps, failSteps, lastSteps));

});
