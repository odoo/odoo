/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('survey_tour_test_survey_form_triggers', {
    test: true,
    url: '/web',
}, [
    tour.stepUtils.showAppsMenuItem(),
    {
        content: 'Go to Survey',
        trigger: '.o_app[data-menu-xmlid="survey.menu_surveys"]',
    }, {
        content: "Create a new survey",
        trigger: ".o-kanban-button-new",
    }, {
        content: "Set the Survey's title",
        trigger: ".o_field_widget[name=title] input",
        run: "text Test survey",
    }, {
        content: "Add a first question",
        trigger: "td.o_field_x2many_list_row_add a",
    }, {
        content: "Set the first question's title",
        trigger: ".modal-content .o_field_widget[name=title] input",
        run: "text Question 1",
    },
    ...addTwoAnswers(),
    ...saveAndNew(),
    {
        content: "Set the second question's title",
        trigger: ".o_field_widget[name=title] input",
        run: "text Question 2",
        in_modal: true,
    },
    ...addTwoAnswers(),
    ...toggleIsConditional(),
    {
        content: "Set a trigger question for the first question",
        trigger: ".o_field_widget[name=triggering_question_id] input",
        run: "click",
        in_modal: true,
    }, {
        content: "Set the first question as trigger",
        trigger: 'ul.ui-autocomplete a:contains("Question 1")',
        run: 'click',
        in_modal: true,
    }, {
        content: "Set a trigger answer for first question",
        trigger: ".modal-content .o_field_widget[name=triggering_answer_id] input",
        run: "click",
        in_modal: true,
    }, {
        content: "Set the first answer as trigger",
        trigger: 'ul.ui-autocomplete a:contains("Answer A")',
        run: 'click',
    },
    ...changeTab("answers"),
    ...saveAndNew(),
    {
        content: "Set the third question's title",
        trigger: ".o_field_widget[name=title] input",
        run: "text Question 3",
        in_modal: true,
    },
    ...addTwoAnswers(),
    ...toggleIsConditional(),
    {
        content: "Set a trigger question for the second question",
        trigger: ".o_field_widget[name=triggering_question_id] input",
        run: "click",
        in_modal: true,
    }, {
        content: "Set the second question as trigger",
        trigger: 'ul.ui-autocomplete a:contains("Question 2")',
        run: 'click',
        in_modal: true,
    }, {
        content: "Set a trigger answer for second question",
        trigger: ".modal-content .o_field_widget[name=triggering_answer_id] input",
        run: "click",
        in_modal: true,
    }, {
        content: "Set the second answer as trigger",
        trigger: 'ul.ui-autocomplete a:contains("Answer B")',
        run: 'click',
    },
    ...changeTab("answers"),
    ...tour.stepUtils.saveForm(),
    // Q2 and Q3 should have fa-fork icons. Assumes that the Trigger widget's column is 2 places after the title's.
    {
        content: "Check that Question 2 has 'normal' trigger icon",
        trigger: "tr:contains('Question 2') button i.fa-code-fork",
        run: () => {}, // it's a check
    }, {
        content: "Check that Question 3 has 'normal' trigger icon",
        trigger: "tr:contains('Question 3') button i.fa-code-fork",
        run: () => {}, // it's a check
    }, {
        content: "Move Question 3 above its trigger (Question 2)",
        trigger: "tr.o_data_row:nth-child(3) td[name=sequence]",
        run: "drag_and_drop_native div[name=question_and_page_ids] table tbody tr:nth-child(2)",
    }, {
        content: "Check that Question 3 has 'warning' trigger icon",
        trigger: "tr:contains('Question 3') button i.fa-exclamation-triangle",
        run: () => {}, // it's a check
    }, {
        content: "Open that question to check the server's misplacement evaluation agrees",
        trigger: "tr.o_data_row td[data-tooltip='Question 3']",
        run: "click",
    }, {
        content: "Check that an alert is shown",
        trigger: ".o_form_sheet_bg div:first-child.alert-warning:contains('positioned before its trigger')",
        in_modal: true,
    },
    ...changeTab("options"),
    {
        content: "Change trigger question",
        trigger: ".o_field_widget[name=triggering_question_id] input",
        run: "click",
        in_modal: true,
    }, {
        content: "Set the first question as trigger instead",
        trigger: 'ul.ui-autocomplete a:contains("Question 1")',
        run: 'click',
        in_modal: true,
    }, {
        content: "Check that the alert is gone",
        trigger: `.o_form_sheet_bg div:first-child:not(.alert-warning).o_form_sheet`,
        in_modal: true,
        run: () => {}, // it's a check
    }, {
        content: "Change the trigger answer as well",
        trigger: ".modal-content .o_field_widget[name=triggering_answer_id] input",
        run: "click",
        in_modal: true,
    }, {
        content: "Set the second answer as trigger, then",
        trigger: 'ul.ui-autocomplete a:contains("Answer B")',
        run: 'click',
    },
    ...tour.stepUtils.saveForm(),
     {
        content: "Check that Question 3 has its 'normal' trigger icon back",
        trigger: "tr:contains('Question 3') button i.fa-code-fork",
        run: () => {}, // it's a check
    }, {
        content: "Move Question 3 back below Question 2",
        trigger: "tr.o_data_row:nth-child(2) td[name=sequence]",
        run: "drag_and_drop_native div[name=question_and_page_ids] table tbody tr:nth-child(3)",
    }, {
        content: "Open that question again",
        trigger: "tr.o_data_row td[data-tooltip='Question 3']",
        run: "click",
    },
    ...changeTab("options"),
    {
        content: "Change trigger to confirm we can now use Question 2 again",
        trigger: ".modal-content .o_field_widget[name=triggering_question_id] input",
        run: "click",
        in_modal: true,
    }, {
        content: "Question 2 is allowed as trigger again",
        trigger: '.modal-content ul.ui-autocomplete a:contains("Question 2")',
        in_modal: true,
    }, {
        content: "Change the trigger answer back as well",
        trigger: ".modal-content .o_field_widget[name=triggering_answer_id] input",
        run: "text A",
        in_modal: true,
    }, {
        content: "Set the second answer as trigger, then",
        trigger: '.modal-content ul.ui-autocomplete a:contains("Answer B")',
        run: "click",
    },
    ...tour.stepUtils.saveForm(),
    // Deleting trigger answers or whole question gracefully remove the trigger automatically
    {
        content: "Open Question 2 again",
        trigger: "tr.o_data_row td[data-tooltip='Question 2']",
        run: "click",
    }, {
        content: "Delete Answer B",
        trigger: "div[name=suggested_answer_ids] tr:contains('Answer B') button[name=delete]",
    },
    ...tour.stepUtils.saveForm(),
    {
        content: "Check that Question 3 no longer has a trigger icon",
        trigger: "div[name=question_and_page_ids] tr:contains('Question 3') div.o_widget_survey_question_trigger:not(:has(button))",
        run: () => {}, // it's a check
    }, {
        content: "Check that Question 2 however still has a trigger icon",
        trigger: "tr:contains('Question 2') button i.fa-code-fork",
        run: () => {}, // it's a check
    }, {
        content: "Delete Question 1",
        trigger: "tr:contains('Question 1') button[name=delete]",
        run: "click",
    }, {
        content: "Check that now Question 2 too does no longer have a trigger icon",
        trigger: "tr:contains('Question 2') div.o_widget_survey_question_trigger:not(:has(button))",
        run: () => {}, // it's a check
    }, {
        content: 'Go back to Kanban View',
        trigger: 'a[data-menu-xmlid="survey.menu_surveys"]',
    }, {
        content: "Check that we arrived on the kanban view",
        trigger: ".o-kanban-button-new",
        run: () => {}, // it's a check
    }
]);

function addTwoAnswers() {
    return [
        {
            content: "Add the first answer",
            trigger: "div[name=suggested_answer_ids] .o_field_x2many_list_row_add a",
            in_modal: true,
        }, {
            trigger: 'tr.o_selected_row div[name=value] input',
            run: 'text Answer A',
            in_modal: true,
        }, {
            content: "Add the second answer",
            trigger: "div[name=suggested_answer_ids] .o_field_x2many_list_row_add a",
            in_modal: true,
        }, {
            trigger: 'tr.o_selected_row div[name=value] input',
            run: 'text Answer B',
            in_modal: true,
        }
    ];
}

function saveAndNew() {
    return [
        {
            content: "Click Save & New",
            trigger: "button.o_form_button_save_new",
            in_modal: true,
        }, {
            content: "Wait for the dialog to render new question form",
            // suggested_answer_ids required even though in_modal is specified...
            trigger: "div[name=suggested_answer_ids] .o_list_table tbody tr:first-child:not(.o_data_row)", // empty answers list
            in_modal: true,
            run: () => {}, // it's a check
        }
    ];
}

function toggleIsConditional() {
    return [
        ...changeTab("options"),
        {
            content: "Toggle is_conditional",
            trigger: "div[name=is_conditional] input",
            in_modal: true,
            run: "click",
        }
    ];
}

function changeTab(tabName) {
    // Currently, .modal-content is required even though "in_modal"
    return [
        {
            content: `Go to ${tabName} tab`,
            trigger: `.modal-content a[name=${tabName}].nav-link`,
            in_modal: true
        }, {
            content: `Wait for tab ${tabName} tab`,
            trigger: `.modal-content a[name=${tabName}].nav-link.active`,
            in_modal: true,
            run: () => {}, // it's a check
        }
    ];
}
