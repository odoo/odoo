import { registry } from "@web/core/registry";

/**
 * Survey: Q1 -> Q2 -> Q3, `page_per_question`, users can go back.
 * Q3 is only displayed if Q2 is answered with "Answer 1", so Q2 is *potentially* last.
 *
 * With `users_can_go_back`, a simple_choice auto-submits unless the button is "finish",
 * so the button's value at selection time decides where we land.
 *
 * Arriving forward on Q2, `_is_last_page_or_question` renders "Submit" (Q3 inactive).
 * Arriving via "previous", `survey_last` is not computed and the button renders
 * "Continue": `survey_last_triggering_answers` must let the client switch it back to
 * "Submit" when a non-triggering answer is picked, instead of auto-submitting the survey.
 */
registry.category("web_tour.tours").add("test_survey_conditional_questions_submit_button", {
    url: "/survey/start/7d5cf2b0-b9fb-4e0e-a6e2-8a2b4c1d9e30",
    steps: () => [
        {
            content: "Click on Start",
            trigger: 'button.btn:contains("Start")',
            run: "click",
        },
        {
            content: "Answer Q1",
            trigger: 'div.js_question-wrapper:contains("Q1") label:contains("Answer 1")',
            run: "click",
        },
        {
            content: "Q2 is potentially last: the button reads Submit on arrival",
            trigger: '.o_survey_form:has(div.js_question-wrapper:contains("Q2")) button[type=submit][value="finish"]',
        },
        {
            content: "Select the answer of Q2 that triggers Q3",
            trigger: 'div.js_question-wrapper:contains("Q2") label:contains("Answer 1")',
            run: "click",
        },
        {
            content: "The auto-submit navigated to Q3, not to the end of the survey",
            trigger: 'div.js_question-wrapper:contains("Q3")',
        },
        {
            content: "Go back to Q2",
            trigger: 'button[value="previous"]',
            run: "click",
        },
        {
            content: "Q2 is prefilled with the triggering answer",
            trigger: 'div.js_question-wrapper:contains("Q2") label.o_survey_selected:contains("Answer 1")',
        },
        {
            content: "Go back to Q1",
            trigger: 'button[value="previous"]',
            run: "click",
        },
        {
            content: "Refresh while on Q1",
            trigger: 'div.js_question-wrapper:contains("Q1")',
            run: () => window.location.reload(),
            expectUnloadPage: true,
        },
        {
            content: "The survey resumes on Q2, and the trigger is still selected so it reads Continue",
            trigger: '.o_survey_form:has(div.js_question-wrapper:contains("Q2")) button[type=submit][value="next"]',
        },
        {
            content: "Switch to the answer that does not trigger Q3",
            trigger: 'div.js_question-wrapper:contains("Q2") label:contains("Answer 2")',
            run: "click",
        },
        {
            content: "The navigation arrow was switched to finish as well",
            trigger: '.o_survey_navigation_submit[value="finish"]',
        },
        {
            content: "Still on Q2 and the button reads Submit",
            trigger: '.o_survey_form:has(div.js_question-wrapper:contains("Q2")) button[type=submit][value="finish"]:contains("Submit")',
            run: "click",
        },
        {
            content: "Confirm the submission",
            trigger: '.modal button.btn-primary:contains("Submit")',
            run: "click",
        },
        {
            content: "Survey is finished",
            trigger: 'div.o_survey_finished h1:contains("Thank you!")',
        },
    ],
});
