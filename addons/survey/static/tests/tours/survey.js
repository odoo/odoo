odoo.define('survey.tour_test_survey', function (require) {
'use strict';

var tour = require('web_tour.tour');

tour.register('test_survey', {
    test: true,
    url: '/survey/start/b137640d-14d4-4748-9ef6-344ca256531e',
}, [
    // Page-1
    {
        content: 'Click on Start',
        trigger: 'a.btn:contains("Start")',
    }, {
        content: 'Answer Where do you live',
        trigger: 'div.js_question-wrapper:contains("Where do you live") input',
        run: 'text Mordor-les-bains',
    }, {
        content: 'Answer Where do you live',
        trigger: 'div.js_question-wrapper:contains("When is your date of birth") input',
        run: 'text 05/05/1980',
    }, {
        content: 'Answer How frequently do you buy products online',
        trigger: 'div.js_question-wrapper:contains("How frequently do you buy products online") select',
        run: function () {
            var $select = $('div.js_question-wrapper:contains("How frequently do you buy products online") select');
            $select.val($('option:contains("Once a month")').val());
        }
    }, {
        content: 'Answer How many times did you order products on our website',
        trigger: 'div.js_question-wrapper:contains("How many times did you order products on our website") input',
        run: 'text 12',
    }, {
        content: 'Click on Next Page',
        trigger: 'button[value="next"]',
    },
    // Page-2
    {
        content: 'Answer Which of the following words would you use to describe our products (High Quality)',
        trigger: 'div.js_question-wrapper:contains("Which of the following words would you use to describe our products") label:contains("High quality") input',
    }, {
        content: 'Answer Which of the following words would you use to describe our products (Good value for money)',
        trigger: 'div.js_question-wrapper:contains("Which of the following words would you use to describe our products") label:contains("Good value for money") input',
    }, {
        content: 'Answer What do your think about our new eCommerce (The new layout and design is fresh and up-to-date)',
        trigger: 'div.js_question-wrapper:contains("What do your think about our new eCommerce") tr:contains("The new layout and design is fresh and up-to-date") input:first',
    }, {
        content: 'Answer What do your think about our new eCommerce (It is easy to find the product that I want)',
        trigger: 'div.js_question-wrapper:contains("What do your think about our new eCommerce") tr:contains("It is easy to find the product that I want") input:eq(2)',
    }, {
        content: 'Answer What do your think about our new eCommerce (The tool to compare the products is useful to make a choice)',
        trigger: 'div.js_question-wrapper:contains("What do your think about our new eCommerce") tr:contains("The tool to compare the products is useful to make a choice") input:eq(3)',
    }, {
        content: 'Answer What do your think about our new eCommerce (The checkout process is clear and secure)',
        trigger: 'div.js_question-wrapper:contains("What do your think about our new eCommerce") tr:contains("The checkout process is clear and secure") input:eq(2)',
    }, {
        content: 'Answer What do your think about our new eCommerce (I have added products to my wishlist)',
        trigger: 'div.js_question-wrapper:contains("What do your think about our new eCommerce") tr:contains("I have added products to my wishlist") input:last',
    }, {
        content: 'Answer Do you have any other comments, questions, or concerns',
        trigger: 'div.js_question-wrapper:contains("Do you have any other comments, questions, or concerns") textarea',
        run: 'text This is great. Really.',
    }, {
        content: 'Click Submit',
        trigger: 'button[value="finish"]',
    },
    // Final page
    {
        content: 'Thank you',
        trigger: 'h1:contains("Thank you!")',
    }
]);

});
