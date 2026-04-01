import { registry } from "@web/core/registry";
import { expectHiddenQuestion } from "@survey/../tests/tours/survey_chained_conditional_questions";

registry.category("web_tour.tours").add('test_survey_conditional_question_on_different_page', {
    url: '/survey/start/1cb935bd-2399-4ed1-9e10-c649318fb4dc',
    steps: () => [
        {
            content: 'Click on Start',
            trigger: 'button.btn:contains("Start")',
            run: "click",
        }, {
            content: 'Answer Q1 with Answer 1',
            trigger: 'div.js_question-wrapper:contains("Q1") label:contains("Answer 1")',
            run: "click",
        }, {
            content: 'Go to next page',
            trigger: 'button[value="next"]',
            run: "click",
        }, {
            content: 'Check that Q3 is visible',
            trigger: 'div.js_question-wrapper:contains("Q3")',
        }, {
            content: 'Answer Q2 with Answer 2',
            trigger: 'div.js_question-wrapper:contains("Q2") label:contains("Answer 2")',
            run: "click",
        }, {
            content: 'Check that Q3 is still visible',
            trigger: 'div.js_question-wrapper:contains("Q3")',
        }, {
            content: 'Go back',
            trigger: 'button[value="previous"]',
            run: "click",
        }, {
            content: 'Answer Q1 with Answer 2',
            trigger: 'div.js_question-wrapper:contains("Q1") label:contains("Answer 2")',
            run: "click",
        }, {
            content: 'Go to next page',
            trigger: 'button[value="next"]',
            run: "click",
        }, {
            content: 'Check that Q3 is hidden',
            trigger: 'div.js_question-wrapper:contains("Q2")',
            run : () => expectHiddenQuestion("Q3", "Q3 should be hidden as q1_a1 trigger is not selected anymore"),
        }, {
            content: 'Answer Q2 with Answer 1',
            trigger: 'div.js_question-wrapper:contains("Q2") label:contains("Answer 1")',
            run: "click",
        }, {
            content: 'Check that Q3 is now visible again',
            trigger: 'div.js_question-wrapper:contains("Q3")',
        }
    ],
});
