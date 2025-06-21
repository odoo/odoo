/** @odoo-module **/

import { registry } from '@web/core/registry';

registry.category('web_tour.tours').add('test_survey_roaming_mandatory_questions', {
    test: true,
    url: '/survey/start/853ebb30-40f2-43bf-a95a-bbf0e367a365',
    steps: () => [{
        content: 'Click on Start',
        trigger: 'button.btn:contains("Start")',
    }, {
        content: 'Skip question Q1',
        trigger: 'button.btn:contains("Continue")',
    }, {
        content: 'Skip question Q2',
        extra_trigger: 'div.js_question-wrapper:contains("Q2")',
        trigger: 'button.btn:contains("Continue")',
    }, {
        content: 'Check if Q3 button is Submit',
        trigger: 'button.btn:contains("Submit")',
        isCheck: true,
    }, {
        content: 'Go back to Q2',
        trigger: 'button.btn[value="previous"]',
    }, {
        content: 'Check if the alert box is present',
        trigger: 'div.o_survey_question_error span',
        isCheck: true,
    }, {
        content: 'Skip question Q2 again',
        trigger: 'button.btn:contains("Continue")',
    }, {
        content: 'Answer Q3',
        trigger: 'div.js_question-wrapper:contains("Q3") label:contains("Answer 1")',
    }, {
        content: 'Click on Submit',
        trigger: 'button.btn:contains("Submit")',
    }, {
        content: 'Check if question is Q1',
        trigger: 'div.js_question-wrapper:contains("Q1")',
        isCheck: true,
    }, {
        content: 'Click on "Next Skipped" button',
        trigger: 'button.btn:contains("Next Skipped")',
    }, {
        content: 'Check if question is Q2',
        trigger: 'div.js_question-wrapper:contains("Q2")',
        isCheck: true,
    }, {
        content: 'Click on "Next Skipped" button',
        trigger: 'button.btn:contains("Next Skipped")',
    }, {
        content: 'Check if question is Q1 again (should loop on skipped questions)',
        trigger: 'div.js_question-wrapper:contains("Q1")',
        isCheck: true,
    }, {
        content: 'Answer Q1',
        trigger: 'div.js_question-wrapper:contains("Q1") label:contains("Answer 2")',
    }, {
        content: 'Check if the visible question is the skipped question Q2',
        trigger: 'div.js_question-wrapper:contains("Q2")',
        isCheck: true,
    }, {
        content: 'Answer Q2',
        trigger: 'div.js_question-wrapper:contains("Q2") label:contains("Answer 3")',
    }, {
        content: 'Click on Submit',
        trigger: 'button.btn:contains("Submit")',
    }, {
        content: 'Check if the survey is done',
        trigger: 'div.o_survey_finished h1:contains("Thank you!")',
        isCheck: true,
    }],
});
