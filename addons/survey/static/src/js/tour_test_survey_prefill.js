odoo.define('survey.tour_test_survey_prefill', function (require) {
'use strict';

var tour = require('web_tour.tour');

tour.register('test_survey_prefill', {
    test: true,
    url: '/survey/start/b137640d-14d4-4748-9ef6-344ca256531e'
},
[{      // Page-1
        trigger: 'a.btn.btn-primary.btn-lg:contains("Start Survey")',
    }, { // Question: Where do you live ?
        trigger: 'div.js_question-wrapper:contains("Where do you live ?") input',
        run: 'text Grand-Rosiere',
    }, { // Question: When is your date of birth ?
        trigger: 'div.js_question-wrapper:contains("When is your date of birth ?") input',
        run: 'text 05/05/1980',
    }, { // Question: How frequently do you buy products online ?
        trigger: 'div.js_question-wrapper:contains("How frequently do you buy products online ?") select',
        run: 'text 2', // value 2 = 'Once a week'
    }, { // Question: How many times did you order products on our website ?
        trigger: 'div.js_question-wrapper:contains("How many times did you order products on our website ?") input',
        run: 'text 42',
    }, {
        content: 'Click on Next Page',
        trigger: 'button[value="next"]',
    },
    // Page-2
    { // Question: Which of the following words would you use to describe our products ?
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
        run: 'text Is the prefill working?',
    }, {
        content: 'Click on Previous Page',
        trigger: 'button[value="previous"]',
    }, {
        trigger: 'div.js_question-wrapper:contains("How many times did you order products on our website ?") input',
        run: function () {
            // wait for prefill
            // booo ugly (but will be removed when ajax prefill is removed)
            var maxAttempts = 0;
            var checkPrefillLoaded = setInterval(function () {
                if ($('div.js_question-wrapper:contains("How many times did you order products on our website ?") input').val() === '42.0') {
                    $('.o_survey_title').addClass('prefilled');
                    clearInterval(checkPrefillLoaded);
                } else if (maxAttempts >= 50) {
                    clearInterval(checkPrefillLoaded);
                }
                maxAttempts++;
            }, 100); // check every 100ms
        }
    }, {
        trigger: '.o_survey_title.prefilled',
        run: function () {
            // check that all the answers are prefilled in Page 1
            var $inputQ1 = $('div.js_question-wrapper:contains("Where do you live ?") input');
            if ($inputQ1.val() !== 'Grand-Rosiere') {
                return;
            }

            var $inputQ2 = $('div.js_question-wrapper:contains("When is your date of birth ?") input');
            if ($inputQ2.val() !== '05/05/1980') {
                return;
            }

            var $selectQ3 = $('div.js_question-wrapper:contains("How frequently do you buy products online ?") select');
            if ($selectQ3.val() !== $('option:contains("Once a week")').val()) {
                return;
            }

            var $inputQ4 = $('div.js_question-wrapper:contains("How many times did you order products on our website ?") input');
            if ($inputQ4.val() !== '42.0') {
                return;
            }

            $('.o_survey_title').addClass('tour_success');
        }
    }, {
        trigger: '.o_survey_title.tour_success'
    }, {
        content: 'Click on Next Page',
        trigger: 'button[value="next"]',
    }, {
        trigger: 'div.js_question-wrapper:contains("Do you have any other comments, questions, or concerns") textarea',
        run: function () {
            // wait for prefill
            // booo ugly (but will be removed when ajax prefill is removed)
            var maxAttempts = 0;
            var checkPrefillLoaded = setInterval(function () {
                if ($('div.js_question-wrapper:contains("Do you have any other comments, questions, or concerns") textarea').val() === "Is the prefill working?") {
                    $('.o_survey_title').addClass('prefilled2');
                    clearInterval(checkPrefillLoaded);
                } else if (maxAttempts >= 50) {
                    clearInterval(checkPrefillLoaded);
                }
                maxAttempts++;
            }, 100); // check every 100ms
        }
    }, {
        trigger: '.o_survey_title.prefilled2',
        run: function () {
            // check that all the answers are prefilled in Page 2
            var $input1Q1 = $('div.js_question-wrapper:contains("Which of the following words would you use to describe our products") label:contains("High quality") input');
            if (!$input1Q1.is(':checked')) {
                return;
            }

            var $input2Q1 = $('div.js_question-wrapper:contains("Which of the following words would you use to describe our products") label:contains("Good value for money") input');
            if (!$input2Q1.is(':checked')) {
                return;
            }

            var $input1Q2 = $('div.js_question-wrapper:contains("What do your think about our new eCommerce") tr:contains("The new layout and design is fresh and up-to-date") input:first');
            if (!$input1Q2.is(':checked')) {
                return;
            }

            var $input2Q2 = $('div.js_question-wrapper:contains("What do your think about our new eCommerce") tr:contains("It is easy to find the product that I want") input:eq(2)');
            if (!$input2Q2.is(':checked')) {
                return;
            }

            var $input3Q2 = $('div.js_question-wrapper:contains("What do your think about our new eCommerce") tr:contains("The tool to compare the products is useful to make a choice") input:eq(3)');
            if (!$input3Q2.is(':checked')) {
                return;
            }

            var $input4Q2 = $('div.js_question-wrapper:contains("What do your think about our new eCommerce") tr:contains("The checkout process is clear and secure") input:eq(2)');
            if (!$input4Q2.is(':checked')) {
                return;
            }

            var $input5Q2 = $('div.js_question-wrapper:contains("What do your think about our new eCommerce") tr:contains("I have added products to my wishlist") input:last');
            if (!$input5Q2.is(':checked')) {
                return;
            }

            var $inputQ3 = $('div.js_question-wrapper:contains("Do you have any other comments, questions, or concerns") textarea');
            if ($inputQ3.val() !== "Is the prefill working?") {
                return;
            }

            $('.o_survey_title').addClass('tour_success_2');
        }
    }, {
        trigger: '.o_survey_title.tour_success_2'
    }
]);

});
