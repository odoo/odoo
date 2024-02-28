odoo.define('survey.tour_test_survey_chained_conditional_questions', function (require) {
'use strict';

const tour = require('web_tour.tour');

tour.register('test_survey_chained_conditional_questions', {
    test: true,
    url: '/survey/start/3cfadce3-3f7e-41da-920d-10fa0eb19527',
}, [
    {
        content: 'Click on Start',
        trigger: 'button.btn:contains("Start")',
    }, {
        content: 'Answer Q1 with Answer 2',
        trigger: 'div.js_question-wrapper:contains("Q1") label:contains("Answer 2")',
    }, {
        content: 'Check that Q4 and Q5 are visible',
        trigger: 'div.js_question-wrapper:contains(Q4)',
        extra_trigger: 'div.js_question-wrapper:contains(Q5)',
        run: () => {
            const selector = 'div.js_question-wrapper.d-none';
            if (document.querySelectorAll(selector).length !== 2) {
                throw new Error('Q2 and Q3 should be hidden.');
            }
        },
    }, {
        content: 'Answer Q1 with Answer 1',
        trigger: 'div.js_question-wrapper:contains("Q1") label:contains("Answer 1")',
    }, {
        content: 'Answer Q2 with Answer 1',
        trigger: 'div.js_question-wrapper:contains("Q2") label:contains("Answer 1")',
        run: function (actions) {
            const selector = 'div.js_question-wrapper.d-none';
            if (document.querySelectorAll(selector).length !== 3) {
                throw new Error('Q3, Q4 and Q5 should be hidden.');
            }
            // Select Answer 1, in order to trigger the display of Q3.
            actions.click(this.$anchor);
        }
    }, {
        content: 'Answer Q3 with Answer 1',
        trigger: 'div.js_question-wrapper:contains("Q3") label:contains("Answer 1")',
    }, {
        content: 'Answer Q1 with Answer 3',  // This should hide all remaining questions.
        trigger: 'div.js_question-wrapper:contains("Q1") label:contains("Answer 3")',
    }, {
        content: 'Check that only question 1 is now visible',
        trigger: 'div.js_question-wrapper:contains("Q1")',
        run: () => {
            const selector = 'div.js_question-wrapper.d-none';
            if (document.querySelectorAll(selector).length !== 4) {
                throw new Error('Q2, Q3, Q4 and Q5 should have been hidden.');
            }
        }
    }, {
        content: 'Click Submit and finish the survey',
        trigger: 'button[value="finish"]',
    },
    // Final page
    {
        content: 'Thank you',
        trigger: 'h1:contains("Thank you!")',
    }

]);

});
