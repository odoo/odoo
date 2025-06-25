/** @odoo-module **/

import { registry } from '@web/core/registry';

registry.category('web_tour.tours').add('test_survey_roaming_mandatory_questions', {
    url: '/survey/start/853ebb30-40f2-43bf-a95a-bbf0e367a365',
    steps: () => [{
        content: 'Click on Start',
        trigger: 'button.btn:contains("Start")',
        run: "click",
    }, {
        content: 'Skip question Q1',
        trigger: 'button.btn:contains("Continue")',
        run: "click",
    },
    {
        trigger: 'div.js_question-wrapper:contains("Q2")',
    },
    {
        content: 'Skip question Q2',
        trigger: 'button.btn:contains("Continue")',
        run: "click",
    }, {
        content: 'Check if Q3 button is Submit',
        trigger: 'button.btn:contains("Submit")',
    }, {
        content: 'Go back to Q2',
        trigger: 'button.btn[value="previous"]',
        run: "click",
    }, {
        content: 'Check if the alert box is present',
        trigger: 'div.o_survey_question_error span',
    }, {
        content: 'Skip question Q2 again',
        trigger: 'button.btn:contains("Continue")',
        run: "click",
    }, {
        content: 'Answer Q3',
        trigger: 'div.js_question-wrapper:contains("Q3") label:contains("Answer 1")',
        run: "click",
    }, {
        content: 'Click on Submit',
        trigger: 'button.btn:contains("Submit")',
        run: "click",
    }, {
        content: 'Check if question is Q1',
        trigger: 'div.js_question-wrapper:contains("Q1")',
    }, {
        content: 'Click on "Next Skipped" button',
        trigger: 'button.btn:contains("Next Skipped")',
        run: "click",
    }, {
        content: 'Check if question is Q2',
        trigger: 'div.js_question-wrapper:contains("Q2")',
    }, {
        content: 'Click on "Next Skipped" button',
        trigger: 'button.btn:contains("Next Skipped")',
        run: "click",
    }, {
        content: 'Check if question is Q1 again (should loop on skipped questions)',
        trigger: 'div.js_question-wrapper:contains("Q1")',
    }, {
        content: 'Answer Q1',
        trigger: 'div.js_question-wrapper:contains("Q1") label:contains("Answer 2")',
        run: "click",
    }, {
        content: 'Check if the visible question is the skipped question Q2',
        trigger: 'div.js_question-wrapper:contains("Q2")',
    }, {
        content: 'Answer Q2',
        trigger: 'div.js_question-wrapper:contains("Q2") label:contains("Answer 3")',
        run: "click",
    }, {
        content: 'Click on Submit',
        trigger: 'button.btn:contains("Submit")',
        run: "click",
    }, {
        content: 'Check if the survey is done',
        trigger: 'div.o_survey_finished h1:contains("Thank you!")',
    }],
});
