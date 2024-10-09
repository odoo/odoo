/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('survey_tour_test_survey_form_triggers', {
    url: '/odoo',
    steps: () => [
    stepUtils.showAppsMenuItem(),
    {
        content: 'Go to Survey',
        trigger: '.o_app[data-menu-xmlid="survey.menu_surveys"]',
        run: "click",
    }, {
        content: "Create a new survey",
        trigger: ".o-kanban-button-new",
        run: "click",
    }, {
        content: "Set the Survey's title",
        trigger: ".o_field_widget[name=title] textarea",
        run: "edit Test survey",
    }, {
        content: "Add a first question",
        trigger: "td.o_field_x2many_list_row_add a",
        run: "click",
    }, {
        content: "Set the first question's title",
        trigger: ".modal .modal-content .o_field_widget[name=title] input",
        run: "edit Question 1",
    },
    ...addTwoAnswers(),
    ...saveAndNew(),
    {
        content: "Set the second question's title",
        trigger: ".modal .o_field_widget[name=title] input",
        run: "edit Question 2",
    },
    ...addTwoAnswers(),
    ...changeTab("options"),
    {
        content: "Set a trigger for the first question",
        trigger: ".modal .o_field_widget[name=triggering_answer_ids] input",
        run: "click",
    }, {
        content: "Set the first question's first answer as trigger",
        trigger: ".modal ul.ui-autocomplete a:contains(Question 1 : Answer A)",
        run: 'click',
    },
    ...changeTab("answers"),
    ...saveAndNew(),
    {
        content: "Set the third question's title",
        trigger: ".modal .o_field_widget[name=title] input",
        run: "edit Question 3",
    },
    ...addTwoAnswers(),
    ...changeTab("options"),
    {
        content: "Set a trigger for the second question",
        trigger: ".modal .o_field_widget[name=triggering_answer_ids] input",
        run: "click",
    }, {
        content: "Set the second question's second answer as trigger",
        trigger: ".modal ul.ui-autocomplete a:contains(Question 2 : Answer B)",
        run: 'click',
    },
    {
        trigger: ".modal button:contains(save & close)",
        run: "click",
    },
    {
        trigger: "body:not(:has(.modal))",
    },
    {
        content: "Check that Question 2 has 'normal' trigger icon",
        trigger: "tr:contains('Question 2') button i.fa-code-fork",
    }, {
        content: "Check that Question 3 has 'normal' trigger icon",
        trigger: "tr:contains('Question 3') button i.fa-code-fork",
    }, {
        content: "Move Question 3 above its trigger (Question 2)",
        trigger: "div[name=question_and_page_ids] table tr:eq(3) div[name=sequence]",
        run: "drag_and_drop(div[name=question_and_page_ids] table tr:eq(2))",
    }, {
        content: "Check that Question 3 has 'warning' trigger icon",
        trigger: "tr:contains('Question 3') button i.fa-exclamation-triangle",
    }, {
        content: "Open that question to check the server's misplacement evaluation agrees",
        trigger: "tr.o_data_row td:contains('Question 3')",
        run: "click",
    }, {
        content: "Check that an alert is shown",
        trigger: ".modal .o_form_sheet_bg div:first-child.alert-warning:contains('positioned before some or all of its triggers')",
    },
    ...changeTab("options"),
    {
        content: "Remove invalid trigger",
        trigger: ".modal .o_field_widget[name=triggering_answer_ids] span:contains('Question 2') a.o_delete",
        run: "click",
    }, {
        content: "Check that the alert is gone",
        trigger: `.modal .o_form_sheet_bg div:first-child:not(.alert-warning).o_form_sheet`,
    }, {
        content: "Choose a new valid trigger",
        trigger: ".modal .o_field_widget[name=triggering_answer_ids] input",
        run: "click",
    }, {
        content: "Set the first question's second answer as trigger, then",
        trigger: 'ul.ui-autocomplete a:contains("Question 1 : Answer B")',
        run: 'click',
    },
    {
        content: "Save the question (1)",
        trigger: ".modal button:contains(save)",
        run: "click",
    },
    {
        trigger: "body:not(:has(.modal))",
    },
    {
        content: "Check that Question 3 has its 'normal' trigger icon back",
        trigger: "tr:contains('Question 3') button i.fa-code-fork",
    }, {
        content: "Move Question 3 back below Question 2",
        trigger: "div[name=question_and_page_ids] table tr:eq(2) div[name=sequence]",
        run: "drag_and_drop(div[name=question_and_page_ids] table tr:eq(4))",
    }, {
        content: "Open that question again",
        trigger: "tr.o_data_row td:contains('Question 3')",
        run: "click",
    },
    ...changeTab("options"),
    {
        content: "Add a second trigger to confirm we can now use Question 2 again",
        trigger: ".modal .modal-content .o_field_widget[name=triggering_answer_ids] input",
        run: "click",
    }, {
        content: "Add the second question's second answer as trigger, then",
        trigger: '.modal-content ul.ui-autocomplete a:contains("Question 2 : Answer B")',
        run: "click",
    },
    {
        content: "Save the question (2)",
        trigger: ".modal button:contains(save)",
        run: "click",
    },
    {
        trigger: "body:not(:has(.modal))",
    },
    // Move question 1 below question 3,
    {
        content: "Move Question 1 back below Question 3",
        trigger: "div[name=question_and_page_ids] table tr:eq(1) div[name=sequence]",
        run: "drag_and_drop(div[name=question_and_page_ids] table tr:eq(4))",
    }, {
        content: "Check that Question 3 has 'warning' trigger icon",
        trigger: "tr:contains('Question 3') button i.fa-exclamation-triangle",
    }, {
        content: "Open that question again",
        trigger: "tr.o_data_row td:contains('Question 3')",
        run: "click",
    }, {
        content: "Check that an alert is shown also when only one trigger is misplaced",
        trigger: ".modal .o_form_sheet_bg div:first-child.alert-warning:contains('positioned before some or all of its triggers')",
    },
    ...changeTab("options"),
    {
        content: "Remove temporarily used trigger",
        trigger: ".modal .o_field_widget[name=triggering_answer_ids] span:contains('Question 1') a.o_delete",
        run: "click",
    }, {
        content: "Check that the alert is gone in this case too",
        trigger: `.modal .o_form_sheet_bg div:first-child:not(.alert-warning).o_form_sheet`,
    },
    {
        content: "Save the question (3)",
        trigger: ".modal button:contains(save)",
        run: "click",
    },
    {
        trigger: "body:not(:has(.modal))",
    },
    {
        content: "Check that Question 3 has its 'normal' trigger icon back",
        trigger: "tr:contains('Question 3') button i.fa-code-fork",
    }, {
        content: "Move Question 1 back above Question 2",
        trigger: "div[name=question_and_page_ids] table tr:eq(3) div[name=sequence]",
        run: "drag_and_drop(div[name=question_and_page_ids] table tr:eq(1))",
    },
    // Deleting trigger answers or whole question gracefully remove the trigger automatically
    {
        content: "Open Question 2 again",
        trigger: "tr.o_data_row td:contains('Question 2')",
        run: "click",
    }, {
        content: "Delete Answer B",
        trigger: "div[name=suggested_answer_ids] tr:contains('Answer B') button[name=delete]",
        run: "click",
    },
    {
        content: "Save the question (4)",
        trigger: ".modal button:contains(save)",
        run: "click",
    },
    {
        trigger: "body:not(:has(.modal))",
    },
    {
        content: "Check that Question 3 no longer has a trigger icon",
        trigger: "div[name=question_and_page_ids] tr:contains('Question 3') div.o_widget_survey_question_trigger:not(:has(button)):not(:visible)",
    }, {
        content: "Check that Question 2 however still has a trigger icon",
        trigger: "tr:contains('Question 2') button i.fa-code-fork",
    }, {
        content: "Delete Question 1",
        trigger: "tr:contains('Question 1') button[name=delete]",
        run: "click",
    }, {
        content: "Check that now Question 2 too does no longer have a trigger icon",
        trigger: "tr:contains('Question 2') div.o_widget_survey_question_trigger:not(:has(button)):not(:visible)",
    }, {
        content: 'Go back to Kanban View',
        trigger: '[data-menu-xmlid="survey.menu_survey_form"]',
        run: "click",
    }, {
        content: "Check that we arrived on the kanban view",
        trigger: ".o-kanban-button-new",
    }
]});

function addTwoAnswers() {
    return [
        {
            content: "Add the first answer",
            trigger:
                ".modal div[name=suggested_answer_ids] .o_field_x2many_list_row_add a",
            run: "click",
        },
        {
            trigger: ".modal tr.o_selected_row div[name=value] input",
            run: "edit Answer A",
        },
        {
            content: "Add the second answer",
            trigger:
                ".modal div[name=suggested_answer_ids] .o_field_x2many_list_row_add a",
            run: "click",
        },
        {
            trigger:
                ".modal tr:nth-child(2).o_selected_row div[name=value] input",
            run: "edit Answer B",
        },
    ];
}

function saveAndNew() {
    return [
        {
            content: "Click Save & New",
            trigger: ".modal button.o_form_button_save_new",
            run: "click",
        },
        {
            content: "Wait for the dialog to render new question form",
            trigger:
                ".modal div[name=suggested_answer_ids] .o_list_table tbody tr:first-child:not(.o_data_row)", // empty answers list
        },
    ];
}

function changeTab(tabName) {
    return [
        {
            content: `Go to ${tabName} tab`,
            trigger: `.modal .modal-content a[name=${tabName}].nav-link`,
            run: "click",
        },
        {
            content: `Wait for tab ${tabName} tab`,
            trigger: `.modal .modal-content a[name=${tabName}].nav-link.active`,
        },
    ];
}
