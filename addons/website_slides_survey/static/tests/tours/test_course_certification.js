/** @odoo-module */

import tour from 'web_tour.tour';

tour.register('test_course_certification', {
    test: true,
    url: '/survey/start/y137640d-14d4-4748-9ef6-344caaaaaae?answer_token=z137640d-14d4-4748-9ef6-344caaaaaae',
},
[{
        content: "Clicking on Start Certification",
        trigger: 'button.btn.btn-primary.btn-lg:contains("Start Certification")',
    }, { // Answering the question
        trigger: 'div.js_question-wrapper:contains("Question") label:contains("Correct Answer")',
    }, {
        content: "Finish Survey",
        trigger: 'button[type="submit"]',
    }, {
        content: "Thank you",
        trigger: 'h1:contains("Thank you!")',
    }, {
        content: "test passed",
        trigger: 'div:contains("Congratulations, you have passed the test!")',
    }, { // Sharing the certification
        trigger: 'a:contains("Share your certification")'
    }, {
        trigger: '.oe_slide_js_share_email input',
        run: 'text friend@example.com'
    }, {
        trigger: '.oe_slide_js_share_email button',
    }, {
        trigger: '.oe_slide_js_share_email:contains("Sharing is caring")',
        run: function () {}  // check email has been sent
    },
]);
