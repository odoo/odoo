/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Survey: Q1 -> Q2 -> Q3, `page_per_question`, users can go back.
 * Q3 is only displayed if Q2 is answered with "Answer 1", so Q2 is *potentially* last.
 *
 * With `users_can_go_back`, a simple_choice auto-submits unless the button is "finish",
 * so the button's value at selection time decides where we land.
 *
 * Arriving on Q2, the server forces `survey_last` to True (see the stable fail-safe in
 * `_prepare_survey_data`), so the button reads "Submit" whatever is selected. The client
 * then switches it to "Continue" as soon as a triggering answer is picked, using
 * `survey_last_triggering_answers` from the navigation payload.
 *
 * Note: that payload is not available after a hard refresh in this version, since it
 * cannot be passed to the template. The button then stays on "Submit" until the user
 * changes an answer - which is the safe default: clicking it still leads to Q3 when the
 * triggering answer is selected, as the server recomputes the next question.
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
        content: 'Q2 is potentially last: the button reads Submit on arrival',
        extra_trigger: 'div.js_question-wrapper:contains("Q2")',
        trigger: 'button[type="submit"][value="finish"]',
        isCheck: true,
    }, {
        content: 'Select the answer of Q2 that triggers Q3',
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
        content: 'Go back to Q1',
        trigger: 'button[value="previous"]',
    }, {
        content: 'Mark the current document before refreshing',
        trigger: '.o_survey_form div.js_question-wrapper:contains("Q1")',
        run: () => document.querySelector('.o_survey_form').classList.add('o_tour_before_reload'),
    }, {
        content: 'Refresh while on Q1',
        trigger: '.o_survey_form.o_tour_before_reload',
        run: () => window.location.reload(),
    }, {
        content: 'The survey resumes on Q2, with the trigger still selected',
        trigger: '.o_survey_form:not(.o_tour_before_reload) div.js_question-wrapper:contains("Q2") label:contains("Answer 1") input:checked',
        isCheck: true,
    }, {
        // No triggering answers on a hard refresh in this version, so the fail-safe keeps
        // the safe default rather than the "Continue" that 19.0 shows here.
        content: 'The button reads Submit (fail-safe), not Continue',
        trigger: 'button[type="submit"][value="finish"]',
        isCheck: true,
    }, {
        content: 'Switch to the answer that does not trigger Q3',
        trigger: 'div.js_question-wrapper:contains("Q2") label:contains("Answer 2")',
    }, {
        content: 'Still on Q2 and the button reads Submit',
        extra_trigger: 'div.js_question-wrapper:contains("Q2")',
        trigger: 'button[type="submit"][value="finish"]:contains("Submit")',
    }, {
        content: 'Survey is finished',
        trigger: 'div.o_survey_finished h1:contains("Thank you!")',
        isCheck: true,
    }],
});
