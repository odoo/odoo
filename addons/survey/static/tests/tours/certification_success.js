odoo.define('survey.tour_test_certification_success', function (require) {
'use strict';

var tour = require('web_tour.tour');

tour.register('test_certification_success', {
    test: true,
    url: '/survey/start/4ead4bc8-b8f2-4760-a682-1fde8daaaaac'
},
[{ // Page-1
        content: "Clicking on Start Certification",
        trigger: 'a.btn.btn-primary.btn-lg:contains("Start Certification")',
    }, { // Question: Do we sell Acoustic Bloc Screens?
        content: "Selecting answer 'Yes'",
        trigger: 'div.js_question-wrapper:contains("Do we sell Acoustic Bloc Screens") label:contains("Yes") input',
    }, { // Question: Select all the existing products
        content: "Ticking answer 'Chair floor protection'",
        trigger: 'div.js_question-wrapper:contains("Select all the existing products") label:contains("Chair floor protection") input'
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
        content: "Ticking answer 'Legs'",
        trigger: 'div.js_question-wrapper:contains("Select all the available customizations for our Customizable Desk") label:contains("Legs") input'
    }, { // Question: How many versions of the Corner Desk do we have?
        content: "Selecting answer '2'",
        trigger: 'div.js_question-wrapper:contains("How many versions of the Corner Desk do we have") label:contains("2") input',
    }, { // Question: Do you think we have missing products in our catalog? (not rated)
        content: "Missing products",
        trigger: 'div.js_question-wrapper:contains("Do you think we have missing products in our catalog") textarea',
        run: "text I think we should make more versions of the customizable desk, it's such an amazing product!",
    }, { // Page-2 Question: How much do we sell our Cable Management Box?
        content: "Selecting answer '80$' (wrong one)",
        trigger: 'div.js_question-wrapper:contains("How much do we sell our Cable Management Box") label:contains("80$") input',
    }, { // Question: Select all the the products that sell for 100$ or more
        content: "Ticking answer 'Corner Desk Right Sit'",
        trigger: 'div.js_question-wrapper:contains("Select all the the products that sell for 100$ or more") label:contains("Corner Desk Right Sit") input'
    }, {
        content: "Ticking answer 'Desk Combination'",
        trigger: 'div.js_question-wrapper:contains("Select all the the products that sell for 100$ or more") label:contains("Desk Combination") input'
    }, {
        content: "Ticking answer 'Large Desk'",
        trigger: 'div.js_question-wrapper:contains("Select all the the products that sell for 100$ or more") label:contains("Large Desk") input'
    }, { // Question: What do you think about our prices (not rated)?
        content: "Selecting answer 'Underpriced'",
        trigger: 'div.js_question-wrapper:contains("What do you think about our prices") label:contains("Underpriced") input',
    }, {
        content: "Finish Survey",
        trigger: 'button[type="submit"]',
    }, {
        content: "Thank you",
        trigger: 'h1:contains("Thank you!")',
    }, {
        content: "test passed",
        trigger: 'div:contains("Congratulations, you have passed the test!")',
    }
]);

});
