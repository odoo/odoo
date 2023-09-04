/** @odoo-module **/

import { registry } from "@web/core/registry";
import { TourError } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('test_survey_chained_conditional_questions', {
    test: true,
    url: '/survey/start/3cfadce3-3f7e-41da-920d-10fa0eb19527',
    steps: () => [
    {
        content: 'Click on Start',
        trigger: 'button.btn:contains("Start")',
    }, {
        content: 'Answer Q1 with Answer 1',
        trigger: 'div.js_question-wrapper:contains("Q1") label:contains("Answer 1")',
    }, {
        content: 'Answer Q2 with Answer 1',
        trigger: 'div.js_question-wrapper:contains("Q2") label:contains("Answer 1")',
    }, {
        content: 'Answer Q3 with Answer 1',
        trigger: 'div.js_question-wrapper:contains("Q3") label:contains("Answer 1")',
    }, {
        content: 'Answer Q1 with Answer 3',  // This should hide Q2 but not Q3.
        trigger: 'div.js_question-wrapper:contains("Q1") label:contains("Answer 3")',
    }, {
        content: 'Check that Q2 was hidden',
        trigger: 'div.js_question-wrapper:contains("Q3")',
        run : () => expectHiddenQuestion("Q2"),
    }, {
        content: 'Answer Q3 with Answer 2',
        trigger: 'div.js_question-wrapper:contains("Q3") label:contains("Answer 2")',
    }, {
        content: 'Answer Q1 with Answer 2',  // This should hide all other questions.
        trigger: 'div.js_question-wrapper:contains("Q1") label:contains("Answer 2")',
    }, {
        content: 'Check that only question 1 is now visible',
        trigger: 'div.js_question-wrapper:contains("Q1")',
        run : () => {
            expectHiddenQuestion("Q2", "Q2's trigger is gone.");
            expectHiddenQuestion("Q3", "No reason to show it now.");
        },
    }, {
        content: 'Answer Q1 with Answer 3',  // This shows Q3.
        trigger: 'div.js_question-wrapper:contains("Q1") label:contains("Answer 3")',
    }, {
        content: 'Check that a question (Q2) is hidden',
        trigger: 'div.js_question-wrapper:contains("Q1")',
        run : () => expectHiddenQuestion("Q2", "Q2 should stay hidden."),
    }, {
        content: 'Answer Q3 with Answer 2',
        trigger: 'div.js_question-wrapper:contains("Q3") label:contains("Answer 2")',
    }, {
        content: 'Answer Q1 with Answer 2',
        trigger: 'div.js_question-wrapper:contains("Q1") label:contains("Answer 2")',
    }, {
        content: 'Check that only question 1 is now the only one visible again',
        trigger: 'div.js_question-wrapper:contains("Q1")',
        run : () => {
            expectHiddenQuestion("Q2", "Q2's trigger is gone, again.");
            expectHiddenQuestion("Q3", "As Q2's gone, so should this one.");
        },
    }, {
        content: 'Click Submit and finish the survey',
        trigger: 'button[value="finish"]',
    },
    // Final page
    {
        content: 'Thank you',
        trigger: 'h1:contains("Thank you!")',
        isCheck: true,
    }

]});

export function expectHiddenQuestion (questionTitle, msg){
    if ($(`div.js_question-wrapper.d-none:contains('${questionTitle}')`).length !== 1) {
        throw new TourError(msg);
    }
}
