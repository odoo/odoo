/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_survey', {
    url: '/survey/start/b137640d-14d4-4748-9ef6-344caaaaaae',
    steps: () => [
    // Page-1
    {
        content: 'Click on Start',
        trigger: 'button.btn:contains("Start")',
        run: "click",
    }, {
        content: 'Answer Where do you live',
        trigger: 'div.js_question-wrapper:contains("Where do you live") input',
        run: "edit Mordor-les-bains",
    }, {
        content: 'Answer Where do you live',
        trigger: 'div.js_question-wrapper:contains("When is your date of birth") input',
        run: "edit 05/05/1980",
    }, {
        content: 'Answer How frequently do you buy products online',
        trigger: 'div.js_question-wrapper:contains("How frequently do you buy products online") label:contains("Once a month")',
        run: "click",
    }, {
        content: 'Answer How many times did you order products on our website',
        trigger: 'div.js_question-wrapper:contains("How many times did you order products on our website") input',
        run: "edit 12",
    }, {
        content: 'Submit and go to Next Page',
        trigger: 'button[value="next"]',
        run: "click",
    },
    // Page-2
    {
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
        run: "edit This is great. Really.",
    }, {
        content: 'Answer How would you rate your experience on our website?',
        trigger: 'div.js_question-wrapper:contains("How would you rate your experience on our website") label:contains("4")',
        run: "click",
    }, {
        content: 'Click Submit and finish the survey',
        trigger: 'button[value="finish"]',
        run: "click",
    },
    // Final page
    {
        content: 'Thank you',
        trigger: 'h1:contains("Thank you!")',
    }
]});
