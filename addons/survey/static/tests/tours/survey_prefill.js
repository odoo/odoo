/** @odoo-module **/

import { queryFirst, queryOne } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_survey_prefill', {
    url: '/survey/start/b137640d-14d4-4748-9ef6-344caaaaaae',
    steps: () => [{      // Page-1
        trigger: 'button.btn.btn-primary.btn-lg:contains("Start Survey")',
        run: "click",
    }, { // Question: Where do you live?
        trigger: 'div.js_question-wrapper:contains("Where do you live?") input',
        run: "edit Grand-Rosiere",
    }, { // Question: When is your date of birth?
        trigger: 'div.js_question-wrapper:contains("When is your date of birth?") input',
        run: "edit 05/05/1980",
    }, { // Question: How frequently do you buy products online?
        trigger: 'div.js_question-wrapper:contains("How frequently do you buy products online?") label:contains("Once a week")',
        run: "click",
    }, { // Question: How many times did you order products on our website?
        trigger: 'div.js_question-wrapper:contains("How many times did you order products on our website?") input',
        run: "edit 42",
    }, {
        content: 'Click on Next Page',
        trigger: 'button[value="next"]',
        run: "click",
    },
    // Page-2
    { // Question: Which of the following words would you use to describe our products?
        content: 'Answer Which of the following words would you use to describe our products (High Quality)',
        trigger: 'div.js_question-wrapper:contains("Which of the following words would you use to describe our products") label:contains("High quality")',
        run: "click",
    }, {
        content: 'Answer Which of the following words would you use to describe our products (Good value for money)',
        trigger: 'div.js_question-wrapper:contains("Which of the following words would you use to describe our products") label:contains("Good value for money")',
        run: "click",
    }, {
        content: 'Answer What do your think about our new eCommerce (The new layout and design is fresh and up-to-date)',
        trigger: 'div.js_question-wrapper:contains("What do your think about our new eCommerce") tr:contains("The new layout and design is fresh and up-to-date") td:first',
        run: "click",
    }, {
        content: 'Answer What do your think about our new eCommerce (It is easy to find the product that I want)',
        trigger: 'div.js_question-wrapper:contains("What do your think about our new eCommerce") tr:contains("It is easy to find the product that I want") td:eq(2)',
        run: "click",
    }, {
        content: 'Answer What do your think about our new eCommerce (The tool to compare the products is useful to make a choice)',
        trigger: 'div.js_question-wrapper:contains("What do your think about our new eCommerce") tr:contains("The tool to compare the products is useful to make a choice") td:eq(3)',
        run: "click",
    }, {
        content: 'Answer What do your think about our new eCommerce (The checkout process is clear and secure)',
        trigger: 'div.js_question-wrapper:contains("What do your think about our new eCommerce") tr:contains("The checkout process is clear and secure") td:eq(2)',
        run: "click",
    }, {
        content: 'Answer What do your think about our new eCommerce (I have added products to my wishlist)',
        trigger: 'div.js_question-wrapper:contains("What do your think about our new eCommerce") tr:contains("I have added products to my wishlist") td:last',
        run: "click",
    }, {
        content: 'Answer Do you have any other comments, questions, or concerns',
        trigger: 'div.js_question-wrapper:contains("Do you have any other comments, questions, or concerns") textarea',
        run: "edit Is the prefill working?",
    }, {
        content: 'Answer How would you rate your experience on our website?',
        trigger: 'div.js_question-wrapper:contains("How would you rate your experience on our website") label:contains("4")',
        run: "click",
    }, {
        // Go back to previous page
        content: 'Click on the previous page name in the breadcrumb',
        trigger: 'ol.breadcrumb a:first',
        run: "click",
    }, {
        trigger: 'div.js_question-wrapper:contains("How many times did you order products on our website?") input',
        run: function () {
            const inputQ3 = queryFirst(
                'div.js_question-wrapper:contains("How many times did you order products on our website?") input'
            );
            if (inputQ3.value === "42.0") {
                queryOne(".o_survey_title").classList.add("prefilled");
            }
        }
    }, {
        trigger: '.o_survey_title.prefilled',
        run: function () {
            // check that all the answers are prefilled in Page 1
            var inputQ1 = queryOne('div.js_question-wrapper:contains("Where do you live?") input');
            if (inputQ1.value !== 'Grand-Rosiere') {
                return;
            }

            var inputQ2 = queryOne('div.js_question-wrapper:contains("When is your date of birth?") input');
            if (inputQ2.value !== '05/05/1980') {
                return;
            }

            var inputQ3 = queryOne('div.js_question-wrapper:contains("How frequently do you buy products online?") label:contains("Once a week") input');
            if (!inputQ3.checked) {
                return;
            }

            var inputQ4 = queryOne('div.js_question-wrapper:contains("How many times did you order products on our website?") input');
            if (inputQ4.value !== '42.0') {
                return;
            }
            document.querySelector(".o_survey_title").classList.add("tour_success");
        }
    }, {
        trigger: '.o_survey_title.tour_success',
        run: "click",
    }, {
        content: 'Click on Next Page',
        trigger: 'button[value="next"]',
        run: "click",
    }, {
        trigger: 'div.js_question-wrapper:contains("Do you have any other comments, questions, or concerns") textarea',
        run: function () {
            var inputQ3 = queryOne('div.js_question-wrapper:contains("Do you have any other comments, questions, or concerns") textarea');
            if (inputQ3.value === "Is the prefill working?") {
                document.querySelector('.o_survey_title').classList.add('prefilled2');
            }
        }
    }, {
        trigger: '.o_survey_title.prefilled2',
        run: function () {
            // check that all the answers are prefilled in Page 2
            const input1Q1 = queryOne('div.js_question-wrapper:contains("Which of the following words would you use to describe our products") label:contains("High quality") input');
            if (!input1Q1.checked) {
                return;
            }

            const input2Q1 = queryOne('div.js_question-wrapper:contains("Which of the following words would you use to describe our products") label:contains("Good value for money") input');
            if (!input2Q1.checked) {
                return;
            }

            const input1Q2 = queryOne('div.js_question-wrapper:contains("What do your think about our new eCommerce") tr:contains("The new layout and design is fresh and up-to-date") input:first');
            if (!input1Q2.checked) {
                return;
            }

            const input2Q2 = queryOne('div.js_question-wrapper:contains("What do your think about our new eCommerce") tr:contains("It is easy to find the product that I want") input:eq(2)');
            if (!input2Q2.checked) {
                return;
            }

            const input3Q2 = queryOne('div.js_question-wrapper:contains("What do your think about our new eCommerce") tr:contains("The tool to compare the products is useful to make a choice") input:eq(3)');
            if (!input3Q2.checked) {
                return;
            }

            const input4Q2 = queryOne('div.js_question-wrapper:contains("What do your think about our new eCommerce") tr:contains("The checkout process is clear and secure") input:eq(2)');
            if (!input4Q2.checked) {
                return;
            }

            const input5Q2 = queryOne('div.js_question-wrapper:contains("What do your think about our new eCommerce") tr:contains("I have added products to my wishlist") input:last');
            if (!input5Q2.checked) {
                return;
            }

            const inputQ3 = queryOne('div.js_question-wrapper:contains("Do you have any other comments, questions, or concerns") textarea');
            if (inputQ3.value !== "Is the prefill working?") {
                return;
            }

            const inputQ4 = queryOne('div.js_question-wrapper:contains("How would you rate your experience on our website") label:contains("4") input');
            if (!inputQ4.checked) {
                return;
            }

            document.querySelector(".o_survey_title").classList.add("tour_success_2");
        }
    }, {
        trigger: '.o_survey_title.tour_success_2',
    }
]});
