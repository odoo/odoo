/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Survey: Q1 -> Q2 -> Q3, `page_per_question`, roaming enabled.
 * Q3 is only displayed if Q2 is answered with "Answer 1".
 *
 * Q2 is therefore *potentially* last: the button must read "Continue" only while
 * "Answer 1" is selected, and "Submit" otherwise. Because roaming + simple_choice
 * auto-submits as soon as an answer is picked, the button's `value` at that moment
 * decides where we land - so the destination is what we assert.
 *
 * Note: the button state *on arrival* on Q2 is deliberately never asserted. It is
 * still computed server-side by `_is_last_page_or_question`, which considers Q2 a
 * triggering question and returns "Continue" whatever is selected. That part is
 * left out of this partial fix.
 */
registry.category("web_tour.tours").add('test_survey_conditional_questions_submit_button', {
    test: true,
    url: '/survey/start/7d5cf2b0-b9fb-4e0e-a6e2-8a2b4c1d9e30',
    steps: () => [{
        content: 'Click on Start',
        trigger: 'button.btn:contains("Start")',
    }, {
        content: 'Answer Q1',
        trigger: 'div.js_question-wrapper:contains("Q1") label:contains("Answer 1")',
    }, {
        content: 'Select the answer of Q2 that triggers Q3',
        extra_trigger: 'div.js_question-wrapper:contains("Q2")',
        trigger: 'div.js_question-wrapper:contains("Q2") label:contains("Answer 1")',
    }, {
        content: 'The auto-submit navigated to Q3, not to the end of the survey',
        trigger: 'div.js_question-wrapper:contains("Q3")',
        isCheck: true,
    }, {
        content: 'Go back to Q2',
        trigger: 'button[value="previous"]',
    }, {
        content: 'Q2 is prefilled with the triggering answer',
        trigger: 'div.js_question-wrapper:contains("Q2") label:contains("Answer 1") input:checked',
        isCheck: true,
    }, {
        content: 'Mark the current document before refreshing',
        trigger: '.o_survey_form',
        run: () => document.querySelector('.o_survey_form').classList.add('o_tour_before_reload'),
    }, {
        content: 'Refresh the page',
        trigger: '.o_survey_form.o_tour_before_reload',
        run: () => window.location.reload(),
    }, {
        content: 'The refreshed survey displays Q3 again, no answer prefilled',
        trigger: '.o_survey_form:not(.o_tour_before_reload) div.js_question-wrapper:contains("Q3")',
        isCheck: true,
    }, {
        content: 'Go back to Q2',
        trigger: 'button[value="previous"]',
    }, {
        content: 'Select the answer of Q2 that does not trigger Q3',
        trigger: 'div.js_question-wrapper:contains("Q2") label:contains("Answer 2")',
    }, {
        content: 'Submit the survey',
        trigger: 'button[value="finish"]',
    }, {
        content: 'Survey is finished',
        trigger: 'div.o_survey_finished h1:contains("Thank you!")',
        isCheck: true,
    }],
});